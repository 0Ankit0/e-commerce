'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Shield, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import apiClient from '@/lib/api-client';

interface TwoFactorFormProps {
  isEnabled?: boolean;
  onStatusChange?: (enabled: boolean) => void;
}

export function TwoFactorForm({ isEnabled = false, onStatusChange }: TwoFactorFormProps) {
  const [showSetup, setShowSetup] = useState(false);
  const [qrCode, setQrCode] = useState('');
  const [secret, setSecret] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const initiate2FA = async () => {
    setIsLoading(true);
    setError('');
    try {
      const response = await apiClient.post('/auth/otp/generate/');
      setQrCode(response.data.qr_code);
      setSecret(response.data.secret);
      setShowSetup(true);
    } catch (err) {
      setError('Failed to initiate 2FA setup. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const verify2FA = async () => {
    if (verificationCode.length !== 6) {
      setError('Please enter a 6-digit code');
      return;
    }

    setIsLoading(true);
    setError('');
    try {
      await apiClient.post('/auth/otp/verify/', { code: verificationCode });
      setShowSetup(false);
      onStatusChange?.(true);
    } catch (err) {
      setError('Invalid verification code. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const disable2FA = async () => {
    setIsLoading(true);
    setError('');
    try {
      await apiClient.post('/auth/otp/disable/');
      onStatusChange?.(false);
    } catch (err) {
      setError('Failed to disable 2FA. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Two-Factor Authentication
        </CardTitle>
        <CardDescription>
          Add an extra layer of security to your account
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 p-3 text-sm text-red-600 bg-red-50 rounded-lg">
            {error}
          </div>
        )}

        {isEnabled ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-5 w-5" />
              <span>Two-factor authentication is enabled</span>
            </div>
            <Button
              variant="outline"
              onClick={disable2FA}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <XCircle className="mr-2 h-4 w-4" />
              )}
              Disable 2FA
            </Button>
          </div>
        ) : showSetup ? (
          <div className="space-y-4">
            <div className="text-center">
              <p className="text-sm text-gray-600 mb-4">
                Scan this QR code with your authenticator app:
              </p>
              {qrCode && (
                <img
                  src={qrCode}
                  alt="2FA QR Code"
                  className="mx-auto mb-4"
                />
              )}
              <p className="text-xs text-gray-500 mb-4">
                Or enter this code manually: <code className="bg-gray-100 px-2 py-1 rounded">{secret}</code>
              </p>
            </div>
            <Input
              label="Verification Code"
              placeholder="Enter 6-digit code"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              maxLength={6}
            />
            <div className="flex gap-2">
              <Button onClick={verify2FA} disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Verify & Enable
              </Button>
              <Button variant="outline" onClick={() => setShowSetup(false)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Two-factor authentication adds an extra layer of security by requiring a code from your authenticator app when signing in.
            </p>
            <Button onClick={initiate2FA} disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              <Shield className="mr-2 h-4 w-4" />
              Enable 2FA
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
