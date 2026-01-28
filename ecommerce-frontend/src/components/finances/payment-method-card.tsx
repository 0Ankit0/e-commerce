'use client';

import { CreditCard, Trash2 } from 'lucide-react';
import type { PaymentMethod } from '@/types';
import { Button } from '@/components/ui/button';

interface PaymentMethodCardProps {
  paymentMethod: PaymentMethod;
  isDefault?: boolean;
  onDelete?: () => void;
  onSetDefault?: () => void;
}

const brandIcons: Record<string, string> = {
  visa: '💳',
  mastercard: '💳',
  amex: '💳',
  discover: '💳',
};

export function PaymentMethodCard({
  paymentMethod,
  isDefault = false,
  onDelete,
  onSetDefault,
}: PaymentMethodCardProps) {
  const card = paymentMethod.card;

  if (!card) {
    return null;
  }

  return (
    <div
      className={`p-4 rounded-lg border ${isDefault ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-gray-100 flex items-center justify-center">
            <CreditCard className="h-5 w-5 text-gray-600" />
          </div>
          <div>
            <p className="font-medium text-gray-900 capitalize">
              {card.brand} •••• {card.last4}
            </p>
            <p className="text-sm text-gray-500">
              Expires {card.exp_month}/{card.exp_year}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isDefault && (
            <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full">
              Default
            </span>
          )}
          {!isDefault && onSetDefault && (
            <Button variant="ghost" size="sm" onClick={onSetDefault}>
              Set Default
            </Button>
          )}
          {onDelete && (
            <Button variant="ghost" size="sm" onClick={onDelete}>
              <Trash2 className="h-4 w-4 text-red-500" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
