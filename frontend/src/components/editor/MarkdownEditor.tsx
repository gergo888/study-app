"use client";

import { markdown } from "@codemirror/lang-markdown";
import CodeMirror from "@uiw/react-codemirror";

import { usePrefs } from "@/lib/prefs";

export function MarkdownEditor({
  value,
  onChange,
  height = "60vh",
}: {
  value: string;
  onChange: (v: string) => void;
  height?: string;
}) {
  const { theme } = usePrefs();
  return (
    <div className="md-editor">
      <CodeMirror
        value={value}
        height={height}
        theme={theme === "dark" ? "dark" : "light"}
        extensions={[markdown()]}
        onChange={onChange}
        basicSetup={{ lineNumbers: true, foldGutter: false, highlightActiveLine: true }}
      />
    </div>
  );
}
