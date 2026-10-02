import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { DiagnosticCentre } from '../types';
import { centreService } from '../services/centreService';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { Building2, MapPin, Search, ArrowRight } from 'lucide-react';

export const CentresPage: React.FC = () => {
  const [centres, setCentres] = useState<DiagnosticCentre[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCity, setSelectedCity] = useState('');

  const loadCentres = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await centreService.getCentres({
        city: selectedCity || undefined,
        page: 1,
        page_size: 50,
      });
      setCentres(data.results);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load diagnostic centres';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCentres();
  }, [selectedCity]);

  // Client-side search across name & address
  const filteredCentres = centres.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.address.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.city.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const availableCities = Array.from(new Set(centres.map((c) => c.city))).sort();

  return (
    <div className="space-y-6 py-6">
      <div className="border-b border-slate-200 pb-5">
        <h1 className="text-2xl font-bold text-slate-900">Diagnostic Centres</h1>
        <p className="mt-1 text-sm text-slate-600">
          Browse verified laboratory facilities offering comprehensive diagnostic services.
        </p>
      </div>

      {/* Search and City Filter Controls */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search centres by name or location..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="w-full sm:w-56">
          <select
            value={selectedCity}
            onChange={(e) => setSelectedCity(e.target.value)}
            className="w-full py-2 px-3 text-sm border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Cities</option>
            {availableCities.map((city) => (
              <option key={city} value={city}>
                {city}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <ErrorMessage message={error} onRetry={loadCentres} />}

      {loading ? (
        <LoadingSpinner message="Fetching diagnostic centres from backend..." />
      ) : filteredCentres.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-slate-200">
          <Building2 className="w-10 h-10 text-slate-400 mx-auto mb-2" />
          <p className="text-slate-600 font-medium">No diagnostic centres found</p>
          <p className="text-xs text-slate-400 mt-1">Try changing your search terms or city filter</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredCentres.map((centre) => (
            <div
              key={centre.id}
              className="bg-white border border-slate-200 rounded-lg p-5 flex flex-col justify-between hover:border-blue-300 transition-colors shadow-sm"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-slate-900 text-base">{centre.name}</h3>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700 shrink-0">
                    {centre.city}
                  </span>
                </div>
                <div className="mt-2.5 flex items-start gap-1.5 text-xs text-slate-500">
                  <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                  <span>
                    {centre.address}, {centre.city} - {centre.pincode}
                  </span>
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  Status: <span className="text-emerald-600 font-medium">Active Facility</span>
                </span>
                <Link
                  to={`/centres/${centre.id}`}
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-800"
                >
                  View Details <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
