export async function synthesizeSpeech(
  text: string,
  voice: string = "default",
  engine: string = "edge-tts"
): Promise<Blob> {
  const resp = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice, engine }),
  });
  if (!resp.ok) throw new Error("TTS 请求失败");
  return resp.blob();
}
