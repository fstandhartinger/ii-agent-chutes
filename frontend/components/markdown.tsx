"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import remarkBreaks from "remark-breaks";
import rehypeHighlight from "rehype-highlight";
import rehypeRaw from "rehype-raw";
import rehypeMathJax from "rehype-mathjax";
import rehypeKatex from "rehype-katex";

import "katex/dist/katex.min.css";

interface MarkdownProps {
  children: string | null | undefined;
}

const Markdown = ({ children }: MarkdownProps) => {
  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks, rehypeHighlight, remarkMath]}
        rehypePlugins={[rehypeRaw, rehypeMathJax, rehypeKatex]}
        components={{
          a: ({ ...props }) => (
            <a target="_blank" rel="noopener noreferrer" {...props} />
          ),
          p: ({ children, ...props }) => (
            <p className="mb-4 leading-relaxed" {...props}>{children}</p>
          ),
          ul: ({ children, ...props }) => (
            <ul className="list-disc list-inside mb-4 space-y-2" {...props}>{children}</ul>
          ),
          ol: ({ children, ...props }) => (
            <ol className="list-decimal list-inside mb-4 space-y-2" {...props}>{children}</ol>
          ),
          li: ({ children, ...props }) => (
            <li className="ml-4" {...props}>{children}</li>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
};

export default Markdown;
