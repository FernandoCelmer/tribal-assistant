import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground disabled:pointer-events-none disabled:opacity-40",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary-hover",
        outline: "border border-border bg-transparent text-foreground hover:border-border-hover hover:bg-surface-hover",
        ghost: "text-secondary hover:bg-surface-hover hover:text-foreground",
        destructive: "border border-border text-foreground hover:border-foreground hover:bg-surface-hover",
        danger: "bg-[#dc2626] text-white hover:bg-[#b91c1c] focus-visible:ring-[#f87171]",
      },
      size: { sm: "h-8 px-3", md: "h-9 px-4", lg: "h-[42px] px-[18px] rounded-[7px]", icon: "h-8 w-8" },
    },
    defaultVariants: { variant: "default", size: "md" },
  },
);

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants> & { loading?: boolean };

export function Button({ className, variant, size, loading, disabled, children, ...props }: ButtonProps) {
  return (
    <button className={cn(buttonVariants({ variant, size }), className)} disabled={disabled || loading} aria-busy={loading || undefined} {...props}>
      {loading && <span aria-hidden className="size-3.5 shrink-0 animate-spin rounded-full border-2 border-current/30 border-t-current" />}
      {children}
    </button>
  );
}
