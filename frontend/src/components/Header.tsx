"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/search", label: "Search" },
  { href: "/library", label: "Library" },
  { href: "/onboarding", label: "Topics" },
];

export function Header() {
  const pathname = usePathname();

  return (
    <header className="header">
      <div className="header-inner">
        <Link href="/" className="logo">
          <span className="logo__icon" aria-hidden>
            ◆
          </span>
          Research Feed
        </Link>
        <nav className="header-nav">
          {NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={pathname === href ? "header-nav__link active" : "header-nav__link"}
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
