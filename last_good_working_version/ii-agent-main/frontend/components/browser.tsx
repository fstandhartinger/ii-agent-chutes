import { Globe, SquareArrowOutUpRight } from "lucide-react";
import Image from 'next/image';
import Markdown from "./markdown";

interface BrowserProps {
  className?: string;
  url?: string;
  screenshot?: string;
  raw?: string;
}

const Browser = ({ className, url, screenshot, raw }: BrowserProps) => {
  if (!url) return null;

  return (
    <div
      className={`browser-container border border-[#3A3B3F] rounded-xl overflow-hidden shadow-sm ${className || ''}`}
    >
      <div className="flex items-center gap-3 px-3 py-2.5 bg-black/80 border-b border-neutral-800 flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
            <div className="w-3 h-3 rounded-full bg-[#febc2e]" />
            <div className="w-3 h-3 rounded-full bg-[#28c840]" />
          </div>
        </div>
        <div className="flex-1 flex items-center overflow-hidden">
          <div className="bg-[#35363a] px-3 py-1.5 rounded-lg w-full flex items-center gap-2 group transition-colors">
            <Globe className="h-3.5 w-3.5 text-white flex-shrink-0" />
            <span className="text-sm text-white truncate flex-1 font-medium">
              {url}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            className="p-1.5 rounded-md hover:bg-neutral-800 transition-colors"
            onClick={() => window.open(url, "_blank")}
          >
            <SquareArrowOutUpRight className="h-4 w-4 text-white" />
          </button>
        </div>
      </div>
      <div className="bg-black/80 browser-content">
        {screenshot && (
          <Image
            src={`data:image/jpeg;base64,${screenshot}`}
            alt="Browser"
            layout="fill"
            objectFit="contain"
            className="browser-screenshot"
          />
        )}
        {raw && (
          <div className="p-4 h-full">
            <Markdown>{raw}</Markdown>
          </div>
        )}
      </div>
    </div>
  );
};

export default Browser;
