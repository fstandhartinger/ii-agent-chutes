import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Legal Notice (Imprint) - fubea",
  description: "Legal Notice and Imprint for fubea - Deep Research Agent",
};

export default function Imprint() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="bg-glass rounded-2xl border border-white/10 p-8">
          <h1 className="text-3xl font-bold mb-6 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            fubea Legal Notice (Imprint)
          </h1>
          
          <div className="prose prose-invert max-w-none space-y-6">
            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">Information according to § 5 TMG:</h2>
              <div className="text-muted-foreground space-y-1">
                <p>productivity-boost.com Betriebs UG (haftungsbeschränkt) & Co. KG</p>
                <p>Reichenbergerstr. 2</p>
                <p>94036 Passau</p>
                <p>Germany</p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">Represented by:</h2>
              <p className="text-muted-foreground">Florian Standhartinger</p>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">Contact:</h2>
              <div className="text-muted-foreground space-y-1">
                <p>Phone: +49 178 1981631</p>
                <p>Fax: +49 321 21160681</p>
                <p>
                  Email:{" "}
                  <a 
                    href="mailto:florian.standhartinger@gmail.com" 
                    className="text-blue-400 hover:text-blue-300 transition-colors underline"
                  >
                    florian.standhartinger@gmail.com
                  </a>
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">Commercial Register:</h2>
              <div className="text-muted-foreground space-y-1">
                <p>Registered in the Commercial Register</p>
                <p>Court of Registration: Amtsgericht Passau</p>
                <p>Registration Number: HRB 8453</p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-semibold mb-3 text-white">VAT ID:</h2>
              <div className="text-muted-foreground space-y-1">
                <p>VAT identification number according to § 27a Value Added Tax Act:</p>
                <p>DE296812612</p>
              </div>
            </section>

            <section className="pt-6 border-t border-white/10">
              <p className="text-muted-foreground text-sm">
                © 2024 productivity-boost.com Betriebs UG (haftungsbeschränkt) & Co. KG
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