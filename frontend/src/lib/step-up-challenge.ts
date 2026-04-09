import type { PrivilegedActionChallengeDetail } from '@/types';

export interface StepUpChallengeRequest {
  challenge: PrivilegedActionChallengeDetail;
}

type StepUpChallengeHandler = (request: StepUpChallengeRequest) => Promise<string | null>;

let handler: StepUpChallengeHandler | null = null;

export function registerStepUpChallengeHandler(nextHandler: StepUpChallengeHandler): () => void {
  handler = nextHandler;
  return () => {
    if (handler === nextHandler) {
      handler = null;
    }
  };
}

export async function requestStepUpChallenge(request: StepUpChallengeRequest): Promise<string | null> {
  if (handler) {
    return handler(request);
  }

  if (typeof window === 'undefined') {
    return null;
  }

  const otpCode = window.prompt('Enter your 6-digit OTP code to continue this admin action:');
  return otpCode?.trim() || null;
}
