"""Audio: measure, derive gains, mix, two-pass loudnorm."""
from . import media

TARGET_I, TARGET_TP, TARGET_LRA = -16.0, -1.5, 11.0
BED_FADE_IN = 1.2
BED_FADE_OUT = 2.0


def derive_gains(voice_lufs, bed_lufs, under_voice_lu):
    """Voice is brought to the target loudness; the bed sits `under_voice_lu` LU below it."""
    voice_gain = TARGET_I - voice_lufs
    bed_gain = (TARGET_I - under_voice_lu) - bed_lufs
    return round(voice_gain, 2), round(bed_gain, 2)


def mix_and_normalize(narration, bed, offset, total, under_voice_lu, workdir):
    """Write mixn.wav (two-pass loudnorm, I -16, TP -1.5, LRA 11). Return a dict of what was derived."""
    voice = media.loudnorm_stats(narration)
    bed_m = media.loudnorm_stats(bed, start=0, length=total)
    vg, bg = derive_gains(voice['input_i'], bed_m['input_i'], under_voice_lu)
    delay_ms = int(round(offset * 1000))
    voice_chain = f'aresample=48000,aformat=channel_layouts=stereo,volume={vg}dB'
    if delay_ms:
        voice_chain += f',adelay={delay_ms}|{delay_ms}'
    fc = (f'[0:a]{voice_chain},apad,atrim=0:{total:.3f}[n];'
          f'[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.3f},volume={bg}dB,'
          f'afade=t=in:d={BED_FADE_IN},afade=t=out:st={total - BED_FADE_OUT:.3f}:d={BED_FADE_OUT}[m];'
          f'[n][m]amix=inputs=2:normalize=0:duration=longest[o]')
    media.ffmpeg('-i', narration, '-i', bed, '-filter_complex', fc, '-map', '[o]', '-ar', '48000',
                 '-c:a', 'pcm_f32le', f'{workdir}/mix.wav')
    s = media.loudnorm_stats(f'{workdir}/mix.wav')
    ln = (f'loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:measured_I={s["input_i"]}:'
          f'measured_TP={s["input_tp"]}:measured_LRA={s["input_lra"]}:measured_thresh={s["input_thresh"]}:'
          f'offset={s["target_offset"]}:linear=true,aresample=48000')
    media.ffmpeg('-i', f'{workdir}/mix.wav', '-af', ln, '-c:a', 'pcm_f32le', f'{workdir}/mixn.wav')
    return {'voice_lufs': voice['input_i'], 'bed_lufs': bed_m['input_i'],
            'voice_gain_db': vg, 'bed_gain_db': bg, 'bed_under_voice_lu': round(vg + voice['input_i'] - (bg + bed_m['input_i']), 2),
            'mix_lufs_before_norm': s['input_i'], 'mix_tp_before_norm': s['input_tp']}
