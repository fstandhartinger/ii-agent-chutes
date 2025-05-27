"use client";

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import Cookies from "js-cookie";
import Link from "next/link";

const COOKIE_BANNER_DISMISSED = "fubea_cookie_banner_dismissed";

export default function CookieBanner() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Check if the banner has been dismissed
    const dismissed = Cookies.get(COOKIE_BANNER_DISMISSED);
    if (!dismissed) {
      setIsVisible(true);
    }
  }, []);

  const handleAccept = () => {
    // Set cookie to remember that banner was dismissed
    Cookies.set(COOKIE_BANNER_DISMISSED, "true", {
      expires: 365, // 1 year
      sameSite: "strict",
      secure: window.location.protocol === "https:",
    });
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 p-4">
      <div className="bg-glass-dark border border-white/20 rounded-2xl p-4 mx-auto max-w-4xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex-1 text-sm text-muted-foreground">
            <p>
              We use essential cookies to ensure our service functions properly and to maintain your session. 
              By continuing to use fubea, you consent to our use of these necessary cookies.{" "}
              <Link 
                href="/privacy-policy" 
                className="text-blue-400 hover:text-blue-300 transition-colors underline"
              >
                Learn more
              </Link>
            </p>
          </div>
          <Button
            onClick={handleAccept}
            size="sm"
            className="bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white flex-shrink-0"
          >
            Accept
          </Button>
        </div>
      </div>
    </div>
  );
} 