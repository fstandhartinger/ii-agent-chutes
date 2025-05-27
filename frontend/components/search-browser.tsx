import { SearchIcon } from "lucide-react";

interface SearchBrowserProps {
  className?: string;
  keyword?: string;
  search_results?: string | Record<string, unknown> | undefined;
}

const SearchBrowser = ({
  className,
  keyword,
  search_results,
}: SearchBrowserProps) => {
  if (!keyword) return null;

  return (
    <div
      className={`browser-container flex rounded-xl flex-col overflow-hidden border border-[#3A3B3F] ${className || ''}`}
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
            <SearchIcon className="h-3.5 w-3.5 text-white flex-shrink-0" />
            <span className="text-sm text-white truncate flex-1 font-medium">
              Search: {keyword}
            </span>
          </div>
        </div>
      </div>
      <div className="bg-black/80 browser-content p-4">
        {Array.isArray(search_results) &&
          search_results?.map((item, index) => (
            <div
              key={index}
              className="flex flex-col gap-y-2 py-6 hover:bg-neutral-900/50 transition-all duration-200 px-4 -mx-4 rounded-lg"
            >
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-blue-400 hover:text-blue-300 hover:underline text-lg transition-colors"
              >
                {item.title}
              </a>
              <p className="text-neutral-300 text-sm line-clamp-3 leading-relaxed">
                {item.content}
              </p>
              <span className="text-emerald-400/80 text-xs font-medium">{item.url}</span>
            </div>
          ))}
      </div>
    </div>
  );
};

export default SearchBrowser;
