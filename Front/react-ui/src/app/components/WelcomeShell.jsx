import { useLayoutEffect, useMemo, useRef, useState } from "react";

import { Composer } from "./Composer";
import { InteractiveAvatar } from "./InteractiveAvatar";

function splitWelcomeTitle(text, forceMultiline = false) {
  const value = String(text || "").trim();
  const characters = Array.from(value);
  if (!forceMultiline && characters.length <= 16) {
    return { multiline: false, lines: [value] };
  }

  const commaMatches = Array.from(value.matchAll(/[，,]/g));
  const commaIndex = commaMatches.length
    ? commaMatches[commaMatches.length - 1].index ?? -1
    : -1;
  if (commaIndex >= 0) {
    const firstLine = value.slice(0, commaIndex + 1).trim();
    const secondLine = value.slice(commaIndex + 1).trim();
    if (firstLine && secondLine) {
      return {
        multiline: true,
        lines: [firstLine, secondLine],
      };
    }
  }

  return {
    multiline: true,
    lines: [characters.slice(0, 10).join(""), characters.slice(10).join("")],
  };
}

export function WelcomeShell({ statusText, composerProps }) {
  const titleRef = useRef(null);
  const [forceMultiline, setForceMultiline] = useState(false);
  const titleText = String(statusText || "").trim();

  useLayoutEffect(() => {
    const titleElement = titleRef.current;
    if (!titleElement || !titleText) {
      setForceMultiline(false);
      return undefined;
    }

    const evaluateOverflow = () => {
      const previousWhiteSpace = titleElement.style.whiteSpace;
      const previousDisplay = titleElement.style.display;
      titleElement.style.whiteSpace = "nowrap";
      titleElement.style.display = "block";
      const isOverflowing = titleElement.scrollWidth > titleElement.clientWidth + 1;
      titleElement.style.whiteSpace = previousWhiteSpace;
      titleElement.style.display = previousDisplay;
      setForceMultiline((current) => (current === isOverflowing ? current : isOverflowing));
    };

    const frameId = window.requestAnimationFrame(evaluateOverflow);
    const resizeObserver = typeof ResizeObserver === "function"
      ? new ResizeObserver(() => evaluateOverflow())
      : null;
    resizeObserver?.observe(titleElement);
    if (titleElement.parentElement) {
      resizeObserver?.observe(titleElement.parentElement);
    }
    window.addEventListener("resize", evaluateOverflow);

    return () => {
      window.cancelAnimationFrame(frameId);
      resizeObserver?.disconnect();
      window.removeEventListener("resize", evaluateOverflow);
    };
  }, [titleText]);

  const title = useMemo(
    () => splitWelcomeTitle(titleText, forceMultiline),
    [titleText, forceMultiline],
  );

  return (
    <div className="welcome-stack-shell">
      <section className="hero-panel">
        <InteractiveAvatar className="hero-avatar" alt="鑫哥头像" />
        <div className={`hero-copy${title.multiline ? " is-multiline" : " is-singleline"}`}>
          <h1 ref={titleRef} className={`hero-title${title.multiline ? " is-multiline" : " is-singleline"}`}>
            {title.lines.map((line, index) => (
              <span key={`${line}-${index}`} className="hero-title-line">
                {line}
              </span>
            ))}
          </h1>
        </div>
      </section>

      <Composer {...composerProps} />
    </div>
  );
}
