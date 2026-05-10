import React, { useRef, useState } from "react";
import { Button } from "antd";
import { SoundOutlined, LoadingOutlined } from "@ant-design/icons";
import { synthesizeSpeech } from "@/api/tts";
import { stripMarkdown } from "@/utils/stripMarkdown";

export const VoicePlayer: React.FC<{ text: string }> = ({ text }) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [loading, setLoading] = useState(false);

  const play = async () => {
    setLoading(true);
    try {
      const blob = await synthesizeSpeech(stripMarkdown(text));
      const url = URL.createObjectURL(blob);
      if (audioRef.current) {
        audioRef.current.src = url;
        audioRef.current.play();
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Button
        type="text"
        size="small"
        icon={loading ? <LoadingOutlined /> : <SoundOutlined />}
        onClick={play}
        disabled={loading}
        style={{
          color: "#9ca0ab",
          fontSize: 13,
          padding: "0 4px",
          height: 24,
          borderRadius: 9999,
          transition: "all 200ms cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      />
      <audio ref={audioRef} />
    </>
  );
};
