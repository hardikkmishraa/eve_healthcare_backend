import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Booking } from '../types';
import { bookingService } from '../services/bookingService';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatCurrency, formatDateTime } from '../utils/formatters';
import { Calendar, CreditCard, XCircle, ArrowRight, Clock } from 'lucide-react';

export const MyBookingsPage: React.FC = () => {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const loadBookings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await bookingService.getMyBookings(1, 50);
      setBookings(data.results);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load bookings.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBookings();
  }, []);

  const handleCancel = async (bookingId: string) => {
    if (!window.confirm('Are you sure you want to cancel this diagnostic booking?')) {
      return;
    }

    try {
      setCancellingId(bookingId);
      await bookingService.cancelBooking(bookingId);
      // Reload list to get updated status
      await loadBookings();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to cancel booking.';
      alert(msg);
    } finally {
      setCancellingId(null);
    }
  };

  return (
    <div className="space-y-6 py-6">
      <div className="border-b border-slate-200 pb-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">My Appointments</h1>
          <p className="mt-1 text-sm text-slate-600">
            View your scheduled diagnostic tests, payment status, and appointment history.
          </p>
        </div>
        <Link
          to="/centres"
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors shadow-sm"
        >
          Book New Test <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {error && <ErrorMessage message={error} onRetry={loadBookings} />}

      {loading ? (
        <LoadingSpinner message="Retrieving your bookings..." />
      ) : bookings.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-lg border border-slate-200 shadow-sm">
          <Calendar className="w-12 h-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-900">No bookings found</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
            You have not booked any diagnostic tests yet. Explore our diagnostic centres to schedule one.
          </p>
          <div className="mt-5">
            <Link
              to="/centres"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md"
            >
              Browse Centres
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {bookings.map((b) => (
            <div
              key={b.id}
              className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm hover:border-slate-300 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              {/* Left Column: Details */}
              <div className="space-y-2">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="text-xs font-mono text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                    ID: {b.id.slice(0, 8)}...
                  </span>
                  <StatusBadge status={b.status} />
                </div>

                <div className="flex items-center gap-2 text-slate-800 text-sm font-semibold">
                  <Clock className="w-4 h-4 text-blue-600 shrink-0" />
                  <span>Appointment: {formatDateTime(b.appointment_time)}</span>
                </div>

                {b.notes && (
                  <p className="text-xs text-slate-500 italic max-w-xl">
                    Notes: "{b.notes}"
                  </p>
                )}

                <div className="text-xs text-slate-400">
                  Booked on: {formatDateTime(b.created_at)}
                </div>
              </div>

              {/* Right Column: Amount & Action buttons */}
              <div className="flex flex-row md:flex-col items-center md:items-end justify-between md:justify-center gap-3 pt-3 md:pt-0 border-t md:border-t-0 border-slate-100">
                <div className="text-left md:text-right">
                  <span className="text-xs text-slate-400 block">Total Amount</span>
                  <span className="text-lg font-bold text-slate-900">
                    {formatCurrency(b.total_amount)}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {/* Pay Now button if PENDING */}
                  {b.status === 'PENDING' && (
                    <Link
                      to={`/payment/${b.id}`}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md shadow-sm transition-colors"
                    >
                      <CreditCard className="w-3.5 h-3.5" /> Pay Now
                    </Link>
                  )}

                  {/* Cancel button if PENDING or CONFIRMED */}
                  {(b.status === 'PENDING' || b.status === 'CONFIRMED') && (
                    <button
                      onClick={() => handleCancel(b.id)}
                      disabled={cancellingId === b.id}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-rose-700 hover:text-rose-900 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-md transition-colors disabled:opacity-50"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      {cancellingId === b.id ? 'Cancelling...' : 'Cancel'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
