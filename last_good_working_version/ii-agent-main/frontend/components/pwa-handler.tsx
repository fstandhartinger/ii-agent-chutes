"use client";

import { useEffect } from 'react';
import { toast } from 'sonner';

export default function PWAHandler() {
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js')
        .then((registration) => {
          console.log('Service Worker registered successfully:', registration);
          
          // Check for updates every 30 seconds
          const updateInterval = setInterval(() => {
            registration.update();
          }, 30000);
          
          registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing;
            if (newWorker) {
              newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  // New version available
                  toast.info(
                    'New version available! Click to update.',
                    {
                      duration: 10000,
                      action: {
                        label: 'Update',
                        onClick: () => {
                          newWorker.postMessage({ type: 'SKIP_WAITING' });
                          window.location.reload();
                        }
                      }
                    }
                  );
                }
              });
            }
          });

          // Cleanup interval on unmount
          return () => clearInterval(updateInterval);
        })
        .catch((error) => {
          console.error('Service Worker registration failed:', error);
        });

      // Listen for service worker updates
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        // Service worker has been updated and is now controlling the page
        console.log('Service Worker updated');
      });
    }
  }, []);

  return null; // This component doesn't render anything
} 