"use client";

import { Button } from "@/components/ui/button";
import { Delete } from "lucide-react";

interface NumpadProps {
  value: string;
  onChange: (value: string) => void;
  onEnter?: () => void;
  disabled?: boolean;
}

export function Numpad({ value, onChange, onEnter, disabled }: NumpadProps) {
  const handlePress = (key: string) => {
    if (disabled) return;
    if (key === "backspace") {
      onChange(value.slice(0, -1));
    } else if (key === "00") {
      // Evitar múltiples ceros al inicio
      if (value === "" || value === "0") return;
      onChange(value + "00");
    } else {
      if (value === "0" && key !== "0") {
        onChange(key);
      } else {
        onChange(value + key);
      }
    }
  };

  const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "00", "0", "backspace"];

  return (
    <div className="grid grid-cols-3 gap-2 p-2 bg-muted/20 rounded-xl border">
      {keys.map((key) => (
        <Button
          key={key}
          type="button"
          variant={key === "backspace" ? "destructive" : "secondary"}
          size="lg"
          className="h-16 text-2xl font-medium touch-manipulation active:scale-95 transition-transform"
          onClick={() => handlePress(key)}
          disabled={disabled}
        >
          {key === "backspace" ? <Delete className="h-6 w-6" /> : key}
        </Button>
      ))}
      {onEnter && (
        <Button
          type="button"
          variant="default"
          className="col-span-3 h-14 text-lg font-bold mt-1 shadow-md active:scale-[0.98] transition-transform"
          onClick={onEnter}
          disabled={disabled}
        >
          Confirmar Monto
        </Button>
      )}
    </div>
  );
}
