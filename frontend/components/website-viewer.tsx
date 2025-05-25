"use client";

import { Button } from "@/components/ui/button";
import { Globe } from "lucide-react";

interface WebsiteViewerProps {
  url: string;
  className?: string;
}

const WebsiteViewer = ({ url, className }: WebsiteViewerProps) => {
  return (
    <div className={`flex flex-col h-full ${className}`}>
      <div className="flex-1 bg-white rounded-lg overflow-hidden">
        <iframe
          src={url}
          className="w-full h-full border-0"
          title="Deployed Website"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox"
        />
      </div>
      <div className="p-4 bg-glass-dark border-t border-white/10">
        <Button
          variant="outline"
          size="sm"
          onClick={() => window.open(url, '_blank')}
          className="bg-glass border-white/20 hover:bg-white/10 transition-all-smooth hover-lift"
        >
          <Globe className="w-4 h-4 mr-2" />
          Open in New Tab
        </Button>
      </div>
    </div>
  );
};

export default WebsiteViewer; 