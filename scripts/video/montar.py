"""Monta el video final: quita los tramos de carga (cortes.json), deja 1080x1920 a 30 fps y agrega música CC0.
Uso: python montar.py <carpeta_video> <pista.mp3> <salida.mp4>"""
import json
import subprocess
import sys
from pathlib import Path

carpeta, pista, salida = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
crudo = next((carpeta / "crudo").glob("*.webm"))
cortes = [(a, b) for a, b in json.loads((carpeta / "cortes.json").read_text()) if b - a > 0.05]

quitar = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in cortes) or "0"
video = (f"[0:v]fps=30,select='not({quitar})',setpts=N/30/TB,scale=1080:1920:flags=lanczos,format=yuv420p[v]")
tmp = carpeta / "sin_musica.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(crudo), "-filter_complex", video, "-map", "[v]",
                "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-movflags", "+faststart", str(tmp)], check=True)

dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(tmp)],
                           capture_output=True, text=True, check=True).stdout)
audio = f"volume=0.30,afade=t=in:d=0.8,afade=t=out:st={max(0, dur - 2):.2f}:d=2"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-stream_loop", "-1", "-i", pista, "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-af", audio, "-c:a", "aac", "-b:a", "128k", "-t", f"{dur:.2f}", "-movflags", "+faststart", salida],
               check=True)
print(f"LISTO {salida} {dur:.1f}s, cortes quitados: {len(cortes)} ({sum(b - a for a, b in cortes):.1f}s)")
