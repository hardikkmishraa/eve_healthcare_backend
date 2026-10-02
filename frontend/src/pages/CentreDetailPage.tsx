import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import type { DiagnosticCentre, CentreTestOffering } from '../types';
import { centreService } from '../services/centreService';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatCurrency } from '../utils/formatters';
import { Building2, MapPin, CheckCircle, ArrowLeft, Calendar, FileText } from 'lucide-react';

export const CentreDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [centre, setCentre] = useState<DiagnosticCentre | null>(null);
  const [offerings, setOfferings] = useState<CentreTestOffering[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const [centreData, testsData] = await Promise.all([
        centreService.getCentreById(id),
        centreService.getCentreTests(id),
      ]);
      setCentre(centreData);
      setOfferings(testsData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load centre details';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  if (loading) {
    return <LoadingSpinner message="Loading diagnostic centre offerings..." />;
  }

  if (error || !centre) {
    return (
      <div className="py-8">
        <Link
          to="/centres"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 mb-4"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Centres
        </Link>
        <ErrorMessage message={error || 'Diagnostic centre not found.'} onRetry={loadData} />
      </div>
    );
  }

  return (
    <div className="space-y-6 py-6">
      <Link
        to="/centres"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="w-4 h-4" /> Back to all centres
      </Link>

      {/* Centre Information Header Card */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Building2 className="w-6 h-6 text-blue-600" />
              <h1 className="text-2xl font-bold text-slate-900">{centre.name}</h1>
            </div>
            <p className="mt-2 text-sm text-slate-600 flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-slate-400 shrink-0" />
              {centre.address}, {centre.city} - {centre.pincode}
            </p>
          </div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle className="w-3.5 h-3.5" />
            Verified & Operational
          </div>
        </div>
      </div>

      {/* Available Diagnostic Tests Table / Cards */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Available Diagnostic Tests</h2>
          <p className="text-sm text-slate-500">
            Tests offered at this facility with authoritative laboratory pricing.
          </p>
        </div>

        {offerings.length === 0 ? (
          <div className="text-center py-10 bg-white rounded-lg border border-slate-200">
            <FileText className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <p className="text-sm text-slate-600">No tests currently configured for this centre.</p>
          </div>
        ) : (
          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm">
            <div className="divide-y divide-slate-200">
              {offerings.map((item) => (
                <div
                  key={item.id}
                  className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        {item.test.category}
                      </span>
                      <h3 className="font-semibold text-slate-900 text-base">{item.test.name}</h3>
                    </div>
                    {item.test.description && (
                      <p className="text-xs text-slate-500 max-w-2xl">{item.test.description}</p>
                    )}
                    <div className="text-xs text-slate-400">
                      Sample: <span className="text-slate-600">{item.test.sample_type || 'Blood'}</span>
                    </div>
                  </div>

                  <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-3 shrink-0">
                    <div className="text-right">
                      <span className="text-xs text-slate-400 block">Total Price</span>
                      <span className="text-lg font-bold text-slate-900">
                        {formatCurrency(item.price)}
                      </span>
                    </div>
                    <Link
                      to={`/book?centre_test_id=${item.id}&centre_name=${encodeURIComponent(
                        centre.name
                      )}&test_name=${encodeURIComponent(item.test.name)}&price=${item.price}`}
                      className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors shadow-sm"
                    >
                      <Calendar className="w-4 h-4" /> Book Appointment
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
