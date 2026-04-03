param(
    [string]$OutputName = "stoic_motivacion_voice.mp4",
    [string]$VoiceName = "Microsoft Laura"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$srtPath = Join-Path $baseDir "stoic_motivacion.srt"
$scriptPath = Join-Path $baseDir "stoic_motivacion_guion.txt"
$wavPath = Join-Path $baseDir "stoic_motivacion_voice.wav"
$outputPath = Join-Path $baseDir $OutputName

Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.SelectVoice($VoiceName)
$speaker.Rate = 0
$speaker.Volume = 100
$speaker.SetOutputToWaveFile($wavPath)
$speaker.Speak((Get-Content -Raw $scriptPath))
$speaker.Dispose()

ffmpeg -y `
  -f lavfi -i "color=c=0x0f172a:s=1080x1920:r=30:d=44" `
  -f lavfi -i "sine=frequency=96:duration=44:sample_rate=48000" `
  -i $wavPath `
  -vf "drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='Motivacion Estoica':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=180,drawtext=fontfile='C\:/Windows/Fonts/arial.ttf':text='Disciplina - Claridad - Accion':fontcolor=0x93c5fd:fontsize=36:x=(w-text_w)/2:y=280,subtitles=$srtPath:force_style='FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00303030,BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=120'" `
  -filter_complex "[1:a]volume=0.03[a1];[2:a]volume=1.00[a2];[a1][a2]amix=inputs=2:duration=longest,afade=t=in:st=0:d=1,afade=t=out:st=42:d=2[aout]" `
  -map 0:v -map "[aout]" `
  -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k `
  -shortest `
  $outputPath

Write-Host "Video generado en: $outputPath"
