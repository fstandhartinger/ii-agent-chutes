import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms of Service - fubea",
  description: "Terms of Service for fubea - Deep Research Agent",
};

export default function TermsOfService() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="bg-glass rounded-2xl border border-white/10 p-8">
          <h1 className="text-3xl font-bold mb-6 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            fubea Terms of Service
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
              <h2 className="text-xl font-semibold mb-3 text-white">1. Acceptance of Terms</h2>
              <p className="text-muted-foreground mb-3">
                By accessing or using fubea&apos;s services, you agree to be bound by these Terms of Service and our Privacy Policy. Your use of our service also indicates your acceptance of the terms and conditions of our third-party service providers:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li>Render.com (hosting and infrastructure)</li>
                <li>Chutes.ai (AI processing and inference)</li>
                <li>Various AI models and services accessed through these platforms</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">2. Service Description</h2>
              <p className="text-muted-foreground mb-3">
                fubea provides an AI-powered platform for deep research and analysis. In providing this service, we utilize various third-party AI services and infrastructure providers. By using our service, you acknowledge and agree that your data may be processed by these third-party providers in accordance with their respective terms of service.
              </p>
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                <p className="text-red-200 font-medium">⚠️ Critical Notice</p>
                <p className="text-muted-foreground mt-2">
                  By using fubea, you explicitly acknowledge that your data will be transmitted to and processed by third-party AI services via Render.com and Chutes.ai. If you do not accept this data sharing, you must not use this service.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">3. Use of Service</h2>
              <p className="text-muted-foreground mb-3">
                You agree to:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li>Use the service at your own risk</li>
                <li>Not misuse or abuse the service</li>
                <li>Not submit sensitive, confidential, or personal information</li>
                <li>Comply with all applicable laws and regulations</li>
                <li>Accept that your data will be processed by third-party AI services</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">4. Intellectual Property</h2>
              <p className="text-muted-foreground">
                All rights, title, and interest in the service remain with productivity-boost.com Betriebs UG (haftungsbeschränkt) & Co. KG and its licensors.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">5. Disclaimer of Warranties</h2>
              <p className="text-muted-foreground">
                The service is provided &ldquo;as is&rdquo; without any warranties of any kind, either express or implied. We make no warranties regarding the accuracy, reliability, or availability of the service or any results produced by AI processing.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">6. Limitation of Liability</h2>
              <p className="text-muted-foreground mb-3">
                fubea and productivity-boost.com Betriebs UG (haftungsbeschränkt) & Co. KG shall not be liable for any:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li>Direct, indirect, or consequential damages</li>
                <li>Loss of data or profits</li>
                <li>Service interruptions</li>
                <li>Accuracy of analysis results</li>
                <li>Actions or omissions of third-party service providers</li>
                <li>Data processing by third-party AI services</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">7. Indemnification</h2>
              <p className="text-muted-foreground">
                You agree to indemnify and hold harmless fubea, productivity-boost.com Betriebs UG (haftungsbeschränkt) & Co. KG, and our service providers from any claims arising from your use of the service.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">8. Service Availability and Modifications</h2>
              <p className="text-muted-foreground mb-3">
                We reserve the right to:
              </p>
              <ul className="list-disc list-inside text-muted-foreground space-y-1">
                <li>Modify, suspend, or discontinue any aspect of the service at any time</li>
                <li>Impose limits on certain features or restrict access to parts or all of the service</li>
                <li>Change these terms at any time</li>
              </ul>
              <p className="text-muted-foreground mt-3">
                No specific level of service availability or uptime is guaranteed. The service is provided on an &ldquo;as available&rdquo; basis.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">9. AI Regulation Compliance</h2>
              <p className="text-muted-foreground">
                Our service aims to comply with applicable AI regulations, including the EU AI Act. As regulations evolve, we may need to modify our service or these terms to maintain compliance. Users in the European Union acknowledge that they will use our service in accordance with applicable AI regulations.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">10. Governing Law</h2>
              <p className="text-muted-foreground">
                These terms are governed by the laws of Germany.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">11. Contact</h2>
              <p className="text-muted-foreground">
                For questions about these terms, contact:{" "}
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