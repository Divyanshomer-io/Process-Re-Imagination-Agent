import { cn } from "../ui/utils";

interface Step {
  number: number;
  label: string;
}

interface ProcessStepperProps {
  steps: Step[];
  currentStep: number;
}

export function ProcessStepper({ steps, currentStep }: ProcessStepperProps) {
  return (
    <div className="flex items-center gap-4">
      {steps.map((step, index) => (
        <div key={step.number} className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-full border-2",
                currentStep === step.number
                  ? "border-accent bg-accent text-accent-foreground"
                  : currentStep > step.number
                  ? "border-accent bg-accent text-accent-foreground"
                  : "border-border bg-background text-muted-foreground"
              )}
            >
              {step.number}
            </div>
            <span
              className={cn(
                "text-[var(--text-base)]",
                currentStep >= step.number ? "text-foreground" : "text-muted-foreground"
              )}
            >
              {step.label}
            </span>
          </div>
          {index < steps.length - 1 && (
            <div
              className={cn(
                "h-0.5 w-16",
                currentStep > step.number ? "bg-accent" : "bg-border"
              )}
            />
          )}
        </div>
      ))}
    </div>
  );
}
