import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { DiagnosticTest } from '../types';
import { centreService } from '../services/centreService';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { Search, FlaskConical, ArrowRight } from 'lucide-react';

export const TestsPage: React.FC = () => {
  const [tests, setTests] = useState<DiagnosticTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');

  const loadTests = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await centreService.getTests({
        category: selectedCategory || undefined,
        search: searchTerm || undefined,
        page: 1,
        page_size: 50,
      });
      setTests(data.results);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load diagnostic tests';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTests();
  }, [selectedCategory]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadTests();
  };

  const categories = Array.from(new Set(tests.map((t) => t.category))).sort();

  return (
    <div className="space-y-6 py-6">
      <div className="border-b border-slate-200 pb-5">
        <h1 className="text-2xl font-bold text-slate-900">Diagnostic Tests Catalogue</h1>
        <p className="mt-1 text-sm text-slate-600">
          Explore laboratory pathology, biochemistry, and diagnostic evaluations available at our partner centres.
        </p>
      </div>

      {/* Search and Category Filter */}
      <form
        onSubmit={handleSearchSubmit}
        className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-3 items-center justify-between"
      >
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search tests by name or description..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="w-full sm:w-56">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full py-2 px-3 text-sm border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          className="w-full sm:w-auto px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md shadow-sm"
        >
          Search
        </button>
      </form>

      {error && <ErrorMessage message={error} onRetry={loadTests} />}

      {loading ? (
        <LoadingSpinner message="Loading tests..." />
      ) : tests.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-slate-200">
          <FlaskConical className="w-10 h-10 text-slate-400 mx-auto mb-2" />
          <p className="text-slate-600 font-medium">No diagnostic tests found</p>
          <p className="text-xs text-slate-400 mt-1">Try searching for other medical terms or clearing category filters</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {tests.map((test) => (
            <div
              key={test.id}
              className="bg-white border border-slate-200 rounded-lg p-5 flex flex-col justify-between hover:border-blue-300 transition-colors shadow-sm"
            >
              <div>
                <span className="inline-block px-2.5 py-0.5 rounded text-xs font-semibold bg-blue-50 text-blue-700 mb-2">
                  {test.category}
                </span>
                <h3 className="font-semibold text-slate-900 text-base">{test.name}</h3>
                <p className="mt-1 text-xs text-slate-500 leading-relaxed">
                  {test.description || 'Standard diagnostic test procedure.'}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-slate-500">
                  Sample: <strong className="text-slate-700">{test.sample_type || 'Blood'}</strong>
                </span>
                <Link
                  to="/centres"
                  className="font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  Find Centres <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
