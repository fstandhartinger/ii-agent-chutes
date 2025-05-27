import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy - fubea",
  description: "Privacy Policy for fubea - Deep Research Agent",
};

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="bg-glass rounded-2xl border border-white/10 p-8">
          <h1 className="text-3xl font-bold mb-6 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            fubea Privacy Policy
          </h1>
          
          <p className="text-sm text-muted-foreground mb-8">
            Last updated: {new Date().toLocaleDateString('en-US', { 
              year: 'numeric', 
              month: 'long', 
              day: 'numeric' 
            })}
          </p>

          <div className="prose prose-invert max-w-none space-y-6">
            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">1. Introduction</h2>
              <p className="text-muted-foreground">
                fubea (&ldquo;we&rdquo;, &ldquo;our&rdquo;, or &ldquo;us&rdquo;) is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and safeguard your information when you use our website and AI research services.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">2. Information We Collect</h2>
              <p className="text-muted-foreground mb-3">
                We collect information that you provide directly to us:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li>Research queries and prompts submitted to our service</li>
                <li>Files and documents uploaded for analysis (temporarily processed and not stored)</li>
                <li>Usage data and logs for service improvement</li>
                <li>Device information and session data (stored locally in your browser)</li>
                <li>Service usage metrics and performance data</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">3. Use of Submitted Data</h2>
              <p className="text-muted-foreground mb-3">
                Data submitted to our service is:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li>Processed temporarily for research and analysis purposes only</li>
                <li>Not permanently stored on our servers</li>
                <li>Automatically deleted after processing</li>
                <li>Shared with third-party AI services as necessary for processing (see section 7)</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">4. Cookies and Tracking</h2>
              <p className="text-muted-foreground mb-3">
                We use cookies and similar tracking technologies to:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li>Maintain your session and device identification</li>
                <li>Remember your preferences and consent choices</li>
                <li>Ensure service functionality and continuity</li>
              </ul>
              <p className="text-muted-foreground mt-3">
                Essential cookies are required for the service to function properly. By using our service, you consent to the use of these necessary cookies.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">5. Data Security</h2>
              <p className="text-muted-foreground">
                We implement appropriate security measures but cannot guarantee absolute security. Use of our service is at your own risk. We strongly advise against submitting sensitive, confidential, or personal information.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">6. Third-Party Services</h2>
              <p className="text-muted-foreground mb-3">
                We use third-party services for:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li>Hosting and infrastructure (Render.com)</li>
                <li>AI processing and inference (Chutes.ai)</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">7. AI Processing and Third-Party AI Services</h2>
              <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 mb-4">
                <p className="text-yellow-200 font-medium">⚠️ Important Notice</p>
                <p className="text-muted-foreground mt-2">
                  Your data may be processed by various AI services through our infrastructure providers, including but not limited to services accessed via Chutes.ai and Render.com. By using fubea, you acknowledge and accept that your data will be transmitted to and processed by these third-party services.
                </p>
              </div>
              <p className="text-muted-foreground mb-3">
                Each of these services processes data according to their own privacy policies and terms of service. We ensure that data sharing with these services is temporary and limited to what&apos;s necessary for analysis.
              </p>
              <p className="text-muted-foreground">
                <strong>If you are not comfortable with your data being processed by third-party AI services, please do not use this application.</strong>
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">8. Disclaimer of Liability</h2>
              <p className="text-muted-foreground mb-3">
                We provide our services &ldquo;as is&rdquo; and disclaim any liability for:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li>Accuracy of analysis results</li>
                <li>Consequences of using our service</li>
                <li>Any damages arising from service use</li>
                <li>Data processing by third-party services</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">9. EU AI Act Compliance</h2>
              <p className="text-muted-foreground">
                We are committed to complying with the EU AI Act and other applicable AI regulations. We may update our privacy practices as these regulations evolve. Users in the European Union have additional rights regarding automated processing of their data.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">10. Changes to Privacy Policy</h2>
              <p className="text-muted-foreground">
                We reserve the right to modify this Privacy Policy at any time. Continued use of our service after changes constitutes acceptance of the updated policy.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">11. Contact Us</h2>
              <p className="text-muted-foreground">
                For privacy-related questions, contact us at:{" "}
                <a 
                  href="mailto:florian.standhartinger@gmail.com" 
                  className="text-blue-400 hover:text-blue-300 transition-colors underline"
                >
                  florian.standhartinger@gmail.com
                </a>
              </p>
            </section>
          </div>

          <div className="mt-8 pt-6 border-t border-white/10">
            <Link 
              href="/" 
              className="text-blue-400 hover:text-blue-300 transition-colors underline"
            >
              ← Back to fubea
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
} 