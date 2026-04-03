import type { Route } from "./+types/home";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Based Accountant — AI-Powered Accounting Research" },
    {
      name: "description",
      content:
        "Instant answers from MFRS, MPERS, and ITA 1967. The AI-powered research tool for Malaysian accountants.",
    },
    {
      property: "og:title",
      content: "Based Accountant — AI-Powered Accounting Research",
    },
    {
      property: "og:description",
      content:
        "Search every Malaysian accounting standard instantly. AI-powered answers with citations from MFRS, MPERS, and ITA 1967.",
    },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary_large_image" },
    {
      name: "twitter:title",
      content: "Based Accountant — AI-Powered Accounting Research",
    },
    {
      name: "twitter:description",
      content:
        "Search every Malaysian accounting standard instantly. Cited answers in seconds.",
    },
  ];
}

export default function Home() {
  return (
    <main className="flex items-center justify-center min-h-screen">
      <div className="text-center space-y-4 px-4">
        <h1 className="font-display text-5xl text-gray-900 dark:text-gray-100">
          Based Accountant
        </h1>
        <p className="text-lg text-gray-500 dark:text-gray-400">
          Coming soon.
        </p>
      </div>
    </main>
  );
}
