import { useNavigate } from "react-router";
import { Button } from "../ui/button";
import { Sparkles, Brain, Zap, Target, ArrowRight, Cpu, Network, GitBranch } from "lucide-react";
import McCainLogo from "../../../imports/McCainLogo1";

export function StartScreen() {
  const navigate = useNavigate();

  const handleStart = () => {
    navigate('/phase1/step1');
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center relative overflow-hidden">
      {/* Animated Background Grid */}
      <div className="absolute inset-0 opacity-5">
        <div style={{
          backgroundImage: 'linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)',
          backgroundSize: '50px 50px',
          width: '100%',
          height: '100%'
        }} />
      </div>

      {/* McCain Logo - Top Left */}
      <div className="absolute top-8 left-8 z-30" style={{ width: '140px', height: '70px' }}>
        <McCainLogo />
      </div>

      {/* Floating AI Elements - Distributed across the screen */}
      <FloatingElement
        icon={<Brain className="w-8 h-8" />}
        color="var(--accent)"
        bgColor="var(--accent-foreground)"
        size={64}
        position={{ top: '15%', left: '10%' }}
        delay="0s"
      />
      <FloatingElement
        icon={<Zap className="w-6 h-6" />}
        color="var(--primary)"
        bgColor="var(--primary-foreground)"
        size={48}
        position={{ top: '25%', right: '15%' }}
        delay="1s"
      />
      <FloatingElement
        icon={<Target className="w-7 h-7" />}
        color="var(--path-c)"
        bgColor="var(--path-c-light)"
        size={56}
        position={{ bottom: '20%', left: '15%' }}
        delay="2s"
      />
      <FloatingElement
        icon={<Network className="w-6 h-6" />}
        color="var(--path-b)"
        bgColor="var(--path-b-light)"
        size={52}
        position={{ top: '60%', right: '10%' }}
        delay="1.5s"
      />
      <FloatingElement
        icon={<GitBranch className="w-5 h-5" />}
        color="var(--path-a)"
        bgColor="var(--path-a-light)"
        size={44}
        position={{ top: '40%', left: '8%' }}
        delay="2.5s"
      />
      <FloatingElement
        icon={<Sparkles className="w-5 h-5" />}
        color="var(--primary)"
        bgColor="var(--card)"
        size={40}
        position={{ bottom: '15%', right: '20%' }}
        delay="0.5s"
      />

      {/* Main Content */}
      <div className="relative z-10 max-w-4xl mx-auto text-center px-8">
        {/* Logo Badge */}
        <div className="flex items-center justify-center gap-4 mb-8">
          <div className="w-20 h-20 rounded-[var(--radius)] flex items-center justify-center shadow-lg" style={{ backgroundColor: 'var(--primary)' }}>
            <Cpu className="w-10 h-10" style={{ color: 'var(--primary-foreground)' }} strokeWidth={2.5} />
          </div>
        </div>

        <div className="mb-4">
          <h1 style={{ fontSize: '64px', lineHeight: '1.1', marginBottom: '16px' }}>
            Cognitive Process<br />Re-imagination Engine
          </h1>
          <div className="flex items-center justify-center gap-2 mb-6">
            <div style={{ 
              width: '60px', 
              height: '3px', 
              backgroundColor: 'var(--primary)',
              borderRadius: '99px'
            }} />
            <p className="caption" style={{ color: 'var(--primary)', letterSpacing: '2px' }}>
              POWERED BY AI
            </p>
            <div style={{ 
              width: '60px', 
              height: '3px', 
              backgroundColor: 'var(--primary)',
              borderRadius: '99px'
            }} />
          </div>
        </div>

        <p className="mb-12 max-w-2xl mx-auto" style={{ fontSize: 'var(--text-h4)', color: 'var(--muted-foreground)', lineHeight: '1.8' }}>
          Transform your business processes through a structured 3-phase framework.<br />
          Our AI agents analyze, classify, and generate intelligent blueprints<br />
          for process automation and optimization.
        </p>

        {/* Three Phase Journey */}
        <div className="flex items-center justify-center gap-4 mb-12">
          <PhaseCard 
            number="1"
            title="Inputs"
            description="Structured Data Collection"
            color="var(--path-a)"
          />
          <PhaseArrow />
          <PhaseCard 
            number="2"
            title="Reasoning"
            description="AI-Powered Analysis"
            color="var(--path-b)"
          />
          <PhaseArrow />
          <PhaseCard 
            number="3"
            title="Results"
            description="Blueprint Generation"
            color="var(--path-c)"
          />
        </div>

        {/* CTA Button */}
        <div className="mb-10">
          <Button 
            onClick={handleStart} 
            size="lg"
            className="group px-12 py-8 text-lg shadow-2xl"
            style={{ 
              fontSize: 'var(--text-h3)',
              height: 'auto',
              backgroundColor: 'var(--primary)',
              color: 'var(--primary-foreground)'
            }}
          >
            <Sparkles className="mr-3 w-6 h-6" />
            Start Re-imagination
            <ArrowRight className="ml-3 w-6 h-6 group-hover:translate-x-2 transition-transform" />
          </Button>
        </div>

        {/* Feature Pills */}
        <div className="flex items-center justify-center gap-3 flex-wrap max-w-3xl mx-auto">
          <FeaturePill text="Path A/B/C Classification" />
          <FeaturePill text="Cognitive Friction Analysis" />
          <FeaturePill text="Use Case Generation" />
          <FeaturePill text="Process Blueprints" />
        </div>
      </div>

      {/* Bottom Info */}
      <div className="absolute bottom-8 left-0 right-0 text-center z-20">
        
      </div>
    </div>
  );
}

function FloatingElement({ 
  icon, 
  color, 
  bgColor, 
  size, 
  position, 
  delay 
}: { 
  icon: React.ReactNode; 
  color: string; 
  bgColor: string; 
  size: number;
  position: { top?: string; bottom?: string; left?: string; right?: string };
  delay: string;
}) {
  return (
    <div 
      className="absolute animate-pulse" 
      style={{ 
        ...position,
        animation: `pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite`,
        animationDelay: delay
      }}
    >
      <div 
        className="rounded-full border-2 flex items-center justify-center"
        style={{ 
          width: `${size}px`,
          height: `${size}px`,
          borderColor: color,
          backgroundColor: bgColor
        }}
      >
        <div style={{ color }}>{icon}</div>
      </div>
    </div>
  );
}

function PhaseCard({ number, title, description, color }: { 
  number: string; 
  title: string; 
  description: string; 
  color: string;
}) {
  return (
    <div 
      className="p-6 rounded-[var(--radius)] border-2 transition-all hover:scale-105 cursor-default"
      style={{ 
        borderColor: color,
        backgroundColor: `${color}15`,
        width: '200px'
      }}
    >
      <div 
        className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3"
        style={{ backgroundColor: color }}
      >
        <span style={{ 
          fontSize: 'var(--text-h2)', 
          fontWeight: 'var(--font-weight-bold)',
          color: 'white'
        }}>
          {number}
        </span>
      </div>
      <div style={{ fontSize: 'var(--text-h4)', fontWeight: 'var(--font-weight-bold)', marginBottom: '4px', color: 'var(--foreground)' }}>
        {title}
      </div>
      <div style={{ fontSize: 'var(--text-caption)', color: 'var(--muted-foreground)' }}>
        {description}
      </div>
    </div>
  );
}

function PhaseArrow() {
  return (
    <div style={{ color: 'var(--muted-foreground)', fontSize: '32px', fontWeight: 'var(--font-weight-bold)' }}>
      →
    </div>
  );
}

function FeaturePill({ text }: { text: string }) {
  return (
    <div 
      className="px-4 py-2 rounded-full border"
      style={{ 
        backgroundColor: 'var(--muted)',
        borderColor: 'var(--border)',
        fontSize: 'var(--text-caption)',
        color: 'var(--muted-foreground)'
      }}
    >
      {text}
    </div>
  );
}