'use client';

import { Input } from '@/components/ui/input';
import { MapPin } from 'lucide-react';

interface PostcodeInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder: string;
  disabled?: boolean;
}

export default function PostcodeInput({ value, onChange, onSubmit, placeholder, disabled }: PostcodeInputProps) {
  return (
    <div className="relative flex-1">
      <MapPin className="absolute left-3.5 top-3.5 w-4 h-4 text-emerald-600" />
      <Input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && value.trim() && !disabled) onSubmit();
        }}
        className="pl-10 h-11 font-medium rounded-xl text-sm bg-card shadow-xs border-border"
      />
    </div>
  );
}
