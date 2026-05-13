import { useEffect, useState } from "react";

interface ToastProps {
  message: string;
  type?: "success" | "error" | "warn";
  duration?: number;
  onClose: () => void;
}

export function Toast({ message, type = "success", duration = 3000, onClose }: ToastProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(onClose, 300);
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  return (
    <div
      className={`toast ${type !== "success" ? type : ""}`}
      style={{
        opacity: visible ? 1 : 0,
        transition: "opacity 0.3s ease",
      }}
    >
      {type === "success" && "✓ "}
      {type === "error" && "✕ "}
      {type === "warn" && "⚠ "}
      {message}
    </div>
  );
}
