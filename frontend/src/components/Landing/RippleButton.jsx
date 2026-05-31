import React, { useState } from "react";
import { cn } from "../../lib/utils";

export const RippleButton = React.forwardRef(
  (
    { className, children, rippleColor = "#ffffff", duration = "600ms", onClick, ...props },
    ref,
  ) => {
    const [buttonRipples, setButtonRipples] = useState([]);

    const handleClick = (e) => {
      const button = e.currentTarget;
      const rect = button.getBoundingClientRect();
      const size = Math.max(button.clientWidth, button.clientHeight);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;

      const newRipple = { x, y, size, key: Date.now() };
      setButtonRipples((prevRipples) => [...prevRipples, newRipple]);

      if (onClick) {
        onClick(e);
      }
    };

    return (
      <button
        className={cn(
          "relative overflow-hidden rounded-full bg-black px-8 py-3 text-white text-center font-medium shadow-lg transition-colors hover:bg-neutral-900 border border-neutral-800 disabled:pointer-events-none disabled:opacity-50",
          className
        )}
        onClick={handleClick}
        ref={ref}
        {...props}
      >
        <div className="relative z-10">{children}</div>
        <span className="pointer-events-none absolute inset-0 z-0 overflow-hidden rounded-[inherit]">
          {buttonRipples.map((ripple) => (
            <span
              className="absolute rounded-full opacity-0 animate-ripple-effect"
              key={ripple.key}
              style={{
                width: ripple.size,
                height: ripple.size,
                top: ripple.y,
                left: ripple.x,
                backgroundColor: rippleColor,
                animationDuration: duration,
              }}
            />
          ))}
        </span>
      </button>
    );
  }
);

RippleButton.displayName = "RippleButton";
