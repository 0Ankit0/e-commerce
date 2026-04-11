'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { registerStepUpChallengeHandler } from '@/lib/step-up-challenge';
import type { PrivilegedActionChallengeDetail } from '@/types';

interface PendingChallenge {
  challenge: PrivilegedActionChallengeDetail;
  resolve: (otpCode: string | null) => void;
}

export function StepUpChallengeModal() {
  const [pending, setPending] = useState<PendingChallenge | null>(null);
  const [otpCode, setOtpCode] = useState('');

  useEffect(() => {
    const cleanup = registerStepUpChallengeHandler(async ({ challenge }) => {
      return await new Promise<string | null>((resolve) => {
        setOtpCode('');
        setPending({ challenge, resolve });
      });
    });

    return cleanup;
  }, []);

  if (!pending) {
    return null;
  }

  const onCancel = () => {
    pending.resolve(null);
    setPending(null);
  };

  const onContinue = () => {
    const code = otpCode.trim();
    if (!code) {
      return;
    }
    pending.resolve(code);
    setPending(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-labelledby="step-up-challenge-title">
      <div className="absolute inset-0 bg-black/40" onClick={onCancel} />
      <div className="relative w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 id="step-up-challenge-title" className="text-base font-semibold text-gray-900">
          OTP verification required
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          {pending.challenge.message} Enter your 6-digit OTP to continue.
        </p>
        <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          Risk context: {pending.challenge.action} · freshness {pending.challenge.otp.required_freshness_seconds}s · grace {pending.challenge.otp.grace_window_seconds}s
          {pending.challenge.reason ? ` · reason: ${pending.challenge.reason}` : ''}
        </div>
        <Input
          className="mt-4"
          inputMode="numeric"
          maxLength={6}
          value={otpCode}
          onChange={(event) => setOtpCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
          placeholder="123456"
          autoFocus
        />
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onCancel}>
            Cancel
          </Button>
          <Button size="sm" onClick={onContinue} disabled={otpCode.trim().length !== 6}>
            Continue
          </Button>
        </div>
      </div>
    </div>
  );
}
