#!/usr/bin/env python3
"""
Telegram bot — Natural male deepening (free, CPU-only) using WORLD (pyworld) + formant warp + bass filter.

Features:
- Receives Telegram voice messages (ogg/opus), converts to WAV, processes with pyworld
  (F0 shift + spectral envelope formant warp) and returns a natural-sounding deeper male voice.
- Configurable via environment variables or simple /setpitch and /setformant commands.
- Limits duration to avoid excessive CPU/time on free servers.
- Requires ffmpeg installed on the host.
"""
import os
import tempfile
import subprocess
import logging
import numpy as np
import soundfile as sf
import pyworld as pw
from scipy import interpolate

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
    CommandHandler,
)

# ----------------- Configuration (can be overridden by env vars) -----------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or "PUT_YOUR_TOKEN_HERE"

PITCH_SEMITONES = float(os.environ.get("PITCH_SEMITONES", "-6.0"))  # negative => deeper
FORMANT_WARP = float(os.environ.get("FORMANT_WARP", "0.88"))       # <1 => formant down
TARGET_SR = int(os.environ.get("TARGET_SR", "22050"))
BASS_FILTER = os.environ.get("BASS_FILTER", "bass=g=8:f=120:w=0.3")
OUTPUT_BITRATE = os.environ.get("OUTPUT_BITRATE", "64k")
MAX_DURATION = int(os.environ.get("MAX_DURATION", "45"))  # seconds; limit to protect CPU
# ----------------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def semitone_to_ratio(n_semitones: float) -> float:
    return 2.0 ** (n_semitones / 12.0)


def warp_spectral_envelope(sp: np.ndarray, warp: float) -> np.ndarray:
    """
    Warp spectral envelope (sp: frames x fft_bins) along frequency axis by factor warp.
    warp < 1 shifts formants down (toward lower frequencies).
    Uses linear interpolation for each frame.
    """
    frames, bins = sp.shape
    orig_idx = np.linspace(0, bins - 1, bins)
    # target positions sample the original at orig * warp
    target_positions = (np.linspace(0.0, 1.0, bins) * warp) * (bins - 1)
    target_positions = np.clip(target_positions, 0, bins - 1)

    warped = np.zeros_like(sp)
    for i in range(frames):
        f = sp[i]
        interp = interpolate.interp1d(orig_idx, f, kind="linear", bounds_error=False, fill_value=(f[0], f[-1]))
        warped[i] = interp(target_positions)
    return warped


def convert_with_world(in_wav_path: str, out_wav_path: str,
                       pitch_semitones: float = -6.0,
                       formant_warp: float = 0.88,
                       target_sr: int = 22050):
    """
    Load input wav, resample to target_sr, extract WORLD features, modify f0 and spectral envelope,
    resynthesize and save out_wav_path.
    """
    import librosa

    # load and resample to target_sr
    y, sr = librosa.load(in_wav_path, sr=target_sr, mono=True)
    y = y.astype(np.float64)

    # extract F0 and timing
    _f0, t = pw.dio(y, sr, frame_period=5.0)
    f0 = pw.stonemask(y, _f0, t, sr)

    # spectral envelope and aperiodicity
    sp = pw.cheaptrick(y, f0, t, sr)  # shape: frames x fftlen
    ap = pw.d4c(y, f0, t, sr)

    # pitch shift (F0)
    ratio = semitone_to_ratio(pitch_semitones)
    f0_mod = f0 * ratio
    # keep voiced/unvoiced mask
    f0_mod[f0 == 0] = 0.0

    # warp spectral envelope (formant shift)
    sp_warped = warp_spectral_envelope(sp, formant_warp)

    # synthesize
    y_synth = pw.synthesize(f0_mod, sp_warped, ap, sr, frame_period=5.0)

    # normalize
    max_val = np.max(np.abs(y_synth)) + 1e-9
    y_synth = y_synth / max_val * 0.99

    sf.write(out_wav_path, y_synth.astype(np.float32), sr)

# ---------- Bot command handlers ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! من صدای شما را به یک صدای مردِ بم و طبیعی تبدیل می‌کنم.\n\n"
        "فایل صوتی (voice) بفرستید. حداکثر طول پیش‌فرض: {} ثانیه.\n\n"
        "برای تنظیم مقادیر:\n"
        "/setpitch <n>  — نیم‌پرده‌ها (مثلاً -6)\n"
        "/setformant <r> — نسبت فرمَنت (مثلاً 0.88)\n"
        "/settings — نمایش تنظیمات فعلی\n\n"
        "توجه: فقط با رضایت صاحب صدا استفاده کنید."
        .format(MAX_DURATION)
    )

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"تنظیمات فعلی:\n"
        f"- PITCH_SEMITONES = {context.application.bot_data.get('pitch', PITCH_SEMITONES)}\n"
        f"- FORMANT_WARP = {context.application.bot_data.get('formant', FORMANT_WARP)}\n"
        f"- TARGET_SR = {TARGET_SR}\n"
        f"- MAX_DURATION = {MAX_DURATION} s\n"
    )
    await update.message.reply_text(text)

async def setpitch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("استفاده: /setpitch <n>   (مثلاً /setpitch -6)")
        return
    try:
        val = float(context.args[0])
        context.application.bot_data['pitch'] = val
        await update.message.reply_text(f"PITCH_SEMITONES تنظیم شد به {val}")
    except Exception:
        await update.message.reply_text("مقدار نامعتبر است. لطفاً عدد (مثلاً -6) وارد کنید.")

async def setformant_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("استفاده: /setformant <r>   (مثلاً /setformant 0.88)")
        return
    try:
        val = float(context.args[0])
        if not 0.6 <= val <= 1.2:
            await update.message.reply_text("مقدار منطقی بین 0.6 و 1.2 وارد کنید (کم‌تر => بم‌تر).")
            return
        context.application.bot_data['formant'] = val
        await update.message.reply_text(f"FORMANT_WARP تنظیم شد به {val}")
    except Exception:
        await update.message.reply_text("مقدار نامعتبر است. لطفاً عدد (مثلاً 0.88) وارد کنید.")

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.voice:
        await msg.reply_text("لطفاً یک پیام صوتی (voice message) ارسال کنید.")
        return

    voice = msg.voice
    duration = getattr(voice, "duration", None)
    if duration and duration > MAX_DURATION:
        await msg.reply_text(f"طول فایل بیش از حد است ({duration}s). حداکثر مجاز: {MAX_DURATION}s.")
        return

    pitch = context.application.bot_data.get('pitch', PITCH_SEMITONES)
    formant = context.application.bot_data.get('formant', FORMANT_WARP)

    logger.info("Received voice from chat=%s file_id=%s duration=%s", update.effective_chat.id, voice.file_id, duration)

    try:
        with tempfile.TemporaryDirectory() as td:
            input_ogg = os.path.join(td, "input.ogg")
            wav_in = os.path.join(td, "input.wav")
            processed_wav = os.path.join(td, "processed.wav")
            out_ogg = os.path.join(td, "output.ogg")

            # download
            file = await context.bot.get_file(voice.file_id)
            await file.download_to_drive(input_ogg)

            # convert to wav (mono, TARGET_SR)
            cmd = ["ffmpeg", "-y", "-i", input_ogg, "-ar", str(TARGET_SR), "-ac", "1", wav_in]
            subprocess.run(cmd, check=True)

            # process with WORLD
            convert_with_world(wav_in, processed_wav, pitch_semitones=pitch, formant_warp=formant, target_sr=TARGET_SR)

            # post-process: bass + lowpass + encode to opus for Telegram voice
            af_arg = f"{BASS_FILTER},lowpass=f=8000"
            cmd2 = [
                "ffmpeg", "-y", "-i", processed_wav,
                "-af", af_arg,
                "-c:a", "libopus", "-b:a", OUTPUT_BITRATE,
                out_ogg
            ]
            subprocess.run(cmd2, check=True)

            with open(out_ogg, "rb") as f:
                await context.bot.send_voice(
                    chat_id=update.effective_chat.id,
                    voice=f,
                    reply_to_message_id=msg.message_id,
                )

    except subprocess.CalledProcessError:
        logger.exception("ffmpeg failed")
        await update.message.reply_text("خطا در پردازش صوت (ffmpeg). لطفاً مطمئن شوید ffmpeg نصب و در PATH قرار دارد.")
    except Exception:
        logger.exception("processing failed")
        await update.message.reply_text("خطا در پردازش صوت. لطفاً بعداً دوباره تلاش کنید.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # initialize bot_data with defaults
    app.bot_data['pitch'] = PITCH_SEMITONES
    app.bot_data['formant'] = FORMANT_WARP

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("setpitch", setpitch_cmd))
    app.add_handler(CommandHandler("setformant", setformant_cmd))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))

    logger.info("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
