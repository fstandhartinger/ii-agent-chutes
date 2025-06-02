"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import Cookies from "js-cookie";
import Link from "next/link";

interface ConsentDialogProps {
  isOpen: boolean;
  onAccept: () => void;
  onCancel: () => void;
}

export default function ConsentDialog({ isOpen, onAccept, onCancel }: ConsentDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onCancel}
      />
      
      {/* Modal */}
      <div className="relative bg-glass-dark border border-white/20 rounded-2xl p-6 mx-4 max-w-[500px] w-full max-h-[90vh] overflow-y-auto">
        <div className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent mb-2">
              Terms and Privacy Agreement
            </h2>
            <p className="text-muted-foreground text-sm">
              Before using fubea, please review and accept our terms and privacy policy.
            </p>
          </div>
          
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
            <p className="text-yellow-200 font-medium mb-2">⚠️ Important Notice</p>
            <p className="text-sm text-muted-foreground">
              By using fubea, your data will be processed by third-party AI services via Render.com and Chutes.ai. 
              This is necessary for the service to function.
            </p>
          </div>
          
          <p className="text-sm text-muted-foreground">
            By clicking &ldquo;Accept and Continue&rdquo;, you agree to our{" "}
            <Link 
              href="/terms" 
              target="_blank"
              className="text-blue-400 hover:text-blue-300 transition-colors underline"
            >
              Terms of Service
            </Link>
            {" "}and{" "}
            <Link 
              href="/privacy-policy" 
              target="_blank"
              className="text-blue-400 hover:text-blue-300 transition-colors underline"
            >
              Privacy Policy
            </Link>
            .
          </p>
          
          <p className="text-xs text-muted-foreground">
            If you do not agree to these terms or are not comfortable with third-party data processing, 
            please click &ldquo;Cancel&rdquo; and do not use this service.
          </p>

          <div className="flex gap-2 pt-4">
            <Button 
              variant="outline" 
              onClick={onCancel}
              className="bg-glass border-white/20 hover:bg-white/10 flex-1"
            >
              Cancel
            </Button>
            <Button 
              onClick={onAccept}
              className="bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white flex-1"
            >
              Accept and Continue
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Utility functions for consent management
export const CONSENT_COOKIE_NAME = "fubea_consent_accepted";
export const CONSENT_COOKIE_EXPIRY = 365; // 1 year

export function hasUserConsented(): boolean {
  return Cookies.get(CONSENT_COOKIE_NAME) === "true";
}

export function setUserConsent(): void {
  Cookies.set(CONSENT_COOKIE_NAME, "true", {
    expires: CONSENT_COOKIE_EXPIRY,
    sameSite: "strict",
    secure: window.location.protocol === "https:",
  });
}

export function clearUserConsent(): void {
  Cookies.remove(CONSENT_COOKIE_NAME);
} 