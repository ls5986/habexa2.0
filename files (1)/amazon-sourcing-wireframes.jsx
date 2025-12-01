import React, { useState } from 'react';
import { Home, Inbox, Users, Package, Search, Settings, Bell, TrendingUp, TrendingDown, ChevronRight, ExternalLink, MessageCircle, Bookmark, Filter, MoreHorizontal, Check, X, Lock, Unlock, AlertTriangle, Zap } from 'lucide-react';

export default function AmazonSourcingWireframes() {
  const [activeScreen, setActiveScreen] = useState('dashboard');
  const [selectedDeal, setSelectedDeal] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const screens = [
    { id: 'dashboard', name: 'Dashboard', icon: Home },
    { id: 'dealfeed', name: 'Deal Feed', icon: Inbox, badge: 47 },
    { id: 'suppliers', name: 'Suppliers', icon: Users },
    { id: 'products', name: 'Products', icon: Package },
    { id: 'analyze', name: 'Analyze', icon: Search },
    { id: 'settings', name: 'Settings', icon: Settings },
  ];

  const deals = [
    { id: 1, title: 'Sony Wireless Earbuds - Model XYZ', asin: 'B08XYZ1234', cost: 45, sell: 89.99, profit: 18.50, roi: 41, rank: 8432, moq: 24, supplier: 'Wholesale Kings', time: '2 min ago', status: 'profitable', gating: 'ungated' },
    { id: 2, title: 'Premium Kitchen Knife Set - 8 Piece', asin: 'B09ABC5678', cost: 32, sell: 54.99, profit: 8.20, roi: 26, rank: 24892, moq: 12, supplier: 'KitchenPro Deals', time: '18 min ago', status: 'review', gating: 'gated' },
    { id: 3, title: 'Generic Phone Case', asin: 'B07DEF9012', cost: 8, sell: 12.99, profit: -1.20, roi: -8, rank: 892104, moq: 50, supplier: 'BulkDeals', time: '45 min ago', status: 'unprofitable', gating: 'amazon' },
    { id: 4, title: 'Pet Grooming Kit Professional', asin: 'B08PET4567', cost: 28, sell: 59.99, profit: 15.30, roi: 55, rank: 3421, moq: 10, supplier: 'PetDirect', time: '1 hour ago', status: 'profitable', gating: 'ungated' },
  ];

  const suppliers = [
    { id: 1, name: 'Wholesale Kings', initials: 'WK', rating: 4.2, deals: 47, purchased: 12, avgRoi: 32, lastContact: '2 days ago', tags: ['Electronics', 'Wholesale', 'Reliable'] },
    { id: 2, name: 'PetDirect', initials: 'PD', rating: 4.8, deals: 23, purchased: 8, avgRoi: 45, lastContact: '1 week ago', tags: ['Pet Supplies', 'Premium', 'Fast Shipping'] },
    { id: 3, name: 'KitchenPro Deals', initials: 'KP', rating: 3.9, deals: 31, purchased: 5, avgRoi: 28, lastContact: '3 days ago', tags: ['Kitchen', 'Home Goods'] },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'profitable': return 'bg-emerald-500';
      case 'review': return 'bg-amber-500';
      case 'unprofitable': return 'bg-red-500';
      default: return 'bg-gray-400';
    }
  };

  const getGatingBadge = (gating) => {
    switch (gating) {
      case 'ungated': return { icon: Unlock, text: 'Ungated', color: 'text-emerald-600 bg-emerald-50' };
      case 'gated': return { icon: Lock, text: 'Gated', color: 'text-red-600 bg-red-50' };
      case 'amazon': return { icon: AlertTriangle, text: 'Amazon Selling', color: 'text-amber-600 bg-amber-50' };
      default: return { icon: null, text: '', color: '' };
    }
  };

  const Sidebar = () => (
    <div className={`bg-slate-900 text-white flex flex-col transition-all duration-300 ${sidebarCollapsed ? 'w-16' : 'w-60'}`}>
      <div className="p-4 flex items-center gap-3 border-b border-slate-700">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-sm">SF</div>
        {!sidebarCollapsed && <span className="font-semibold">SourceFlow</span>}
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {screens.map((screen) => (
          <button
            key={screen.id}
            onClick={() => setActiveScreen(screen.id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
              activeScreen === screen.id ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            <screen.icon size={20} />
            {!sidebarCollapsed && (
              <>
                <span className="flex-1 text-left text-sm">{screen.name}</span>
                {screen.badge && (
                  <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">{screen.badge}</span>
                )}
              </>
            )}
          </button>
        ))}
      </nav>
      <button
        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        className="p-4 border-t border-slate-700 text-slate-400 hover:text-white text-sm flex items-center justify-center"
      >
        {sidebarCollapsed ? '→' : '← Collapse'}
      </button>
    </div>
  );

  const TopBar = () => (
    <div className="h-14 bg-white border-b flex items-center justify-between px-6">
      <h1 className="text-lg font-semibold text-slate-800">
        {screens.find(s => s.id === activeScreen)?.name}
      </h1>
      <div className="flex items-center gap-4">
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
          <Zap size={16} />
          Quick Analyze
        </button>
        <button className="relative p-2 text-slate-500 hover:text-slate-700">
          <Bell size={20} />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>
        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-medium text-sm">SA</div>
      </div>
    </div>
  );

  const StatCard = ({ icon, label, value, subtext, trend, trendUp }) => (
    <div className="bg-white rounded-xl p-5 border border-slate-200 hover:shadow-md transition-shadow">
      <div className="flex items-center gap-2 text-slate-500 text-sm mb-2">
        {icon}
        {label}
      </div>
      <div className="text-3xl font-bold text-slate-800">{value}</div>
      <div className="flex items-center justify-between mt-2">
        <span className="text-sm text-slate-500">{subtext}</span>
        <span className={`flex items-center gap-1 text-sm ${trendUp ? 'text-emerald-600' : 'text-red-500'}`}>
          {trendUp ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          {trend}
        </span>
      </div>
    </div>
  );

  const DealCard = ({ deal, onClick }) => {
    const gating = getGatingBadge(deal.gating);
    return (
      <div 
        onClick={() => onClick(deal)}
        className="bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md transition-all cursor-pointer group"
      >
        <div className="flex items-start gap-4">
          <div className={`w-3 h-3 rounded-full mt-1.5 ${getStatusColor(deal.status)}`}></div>
          <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center text-slate-400">
            <Package size={20} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-slate-800 truncate group-hover:text-blue-600 transition-colors">{deal.title}</h3>
            <p className="text-sm text-slate-500 font-mono">{deal.asin}</p>
            
            <div className="flex items-center gap-4 mt-3 text-sm">
              <span className="text-slate-600">
                💵 Cost: ${deal.cost} → Sell: ${deal.sell} → <span className={deal.profit > 0 ? 'text-emerald-600 font-medium' : 'text-red-500 font-medium'}>${deal.profit.toFixed(2)}</span>
              </span>
            </div>
            
            <div className="flex items-center gap-3 mt-2">
              <span className={`text-xs px-2 py-1 rounded-full ${deal.roi > 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                📊 ROI: {deal.roi}%
              </span>
              <span className="text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-600">
                📦 MOQ: {deal.moq}
              </span>
              <span className="text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-600">
                📈 #{deal.rank.toLocaleString()}
              </span>
              <span className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 ${gating.color}`}>
                {gating.icon && <gating.icon size={12} />}
                {gating.text}
              </span>
            </div>
            
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100">
              <span className="text-sm text-slate-500">
                👤 {deal.supplier} • {deal.time}
              </span>
              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="flex items-center gap-1 px-3 py-1.5 text-xs text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                  <MessageCircle size={14} />
                  Message
                </button>
                <button className="flex items-center gap-1 px-3 py-1.5 text-xs text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                  <Bookmark size={14} />
                  Save
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const SupplierCard = ({ supplier }) => (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-blue-600 font-bold">
          {supplier.initials}
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-800">{supplier.name}</h3>
            <div className="flex items-center gap-1 text-amber-500">
              {'★'.repeat(Math.floor(supplier.rating))}
              <span className="text-slate-500 text-sm ml-1">({supplier.rating})</span>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-4 mt-4 text-sm">
            <div>
              <div className="text-slate-500">Deals</div>
              <div className="font-medium text-slate-800">{supplier.deals}</div>
            </div>
            <div>
              <div className="text-slate-500">Purchased</div>
              <div className="font-medium text-slate-800">{supplier.purchased}</div>
            </div>
            <div>
              <div className="text-slate-500">Avg ROI</div>
              <div className="font-medium text-emerald-600">{supplier.avgRoi}%</div>
            </div>
            <div>
              <div className="text-slate-500">Last Contact</div>
              <div className="font-medium text-slate-800">{supplier.lastContact}</div>
            </div>
          </div>
          <div className="flex items-center gap-2 mt-4">
            {supplier.tags.map((tag, i) => (
              <span key={i} className="text-xs px-2 py-1 bg-slate-100 text-slate-600 rounded-full">{tag}</span>
            ))}
          </div>
          <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-100">
            <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
              <MessageCircle size={16} />
              Message
            </button>
            <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 rounded-lg transition-colors">
              <Package size={16} />
              Orders
            </button>
            <button className="px-3 py-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-lg transition-colors">
              <MoreHorizontal size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const DealDetailPanel = ({ deal, onClose }) => {
    if (!deal) return null;
    const gating = getGatingBadge(deal.gating);
    
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-end z-50" onClick={onClose}>
        <div className="w-full max-w-lg h-full bg-white overflow-y-auto" onClick={e => e.stopPropagation()}>
          <div className="sticky top-0 bg-white border-b p-4 flex items-center justify-between">
            <h2 className="font-semibold text-slate-800">Product Analysis</h2>
            <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg">
              <X size={20} />
            </button>
          </div>
          
          <div className="p-6">
            <div className="flex items-start gap-4">
              <div className="w-20 h-20 bg-slate-100 rounded-xl flex items-center justify-center text-slate-400">
                <Package size={32} />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-slate-800 text-lg">{deal.title}</h3>
                <p className="text-slate-500 font-mono text-sm">{deal.asin}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className={`text-xs px-2 py-1 rounded-full ${deal.status === 'profitable' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                    {deal.status.toUpperCase()}
                  </span>
                  <span className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 ${gating.color}`}>
                    {gating.icon && <gating.icon size={12} />}
                    {gating.text}
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-4 mt-6">
              <div className="text-center p-4 bg-slate-50 rounded-xl">
                <div className="text-2xl font-bold text-slate-800">${deal.profit.toFixed(2)}</div>
                <div className="text-xs text-slate-500">Profit</div>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-xl">
                <div className={`text-2xl font-bold ${deal.roi > 0 ? 'text-emerald-600' : 'text-red-500'}`}>{deal.roi}%</div>
                <div className="text-xs text-slate-500">ROI</div>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-xl">
                <div className="text-2xl font-bold text-slate-800">#{deal.rank.toLocaleString()}</div>
                <div className="text-xs text-slate-500">Rank</div>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-xl">
                <div className="text-2xl font-bold text-slate-800">~340</div>
                <div className="text-xs text-slate-500">Est/Mo</div>
              </div>
            </div>

            <div className="mt-6 p-4 bg-slate-50 rounded-xl">
              <h4 className="font-medium text-slate-800 mb-3">💰 Profit Breakdown</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-600">Your Cost</span>
                  <span className="text-slate-800">${deal.cost.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">+ Shipping Est.</span>
                  <span className="text-slate-800">$2.50</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">+ Prep Fee</span>
                  <span className="text-slate-800">$1.00</span>
                </div>
                <div className="border-t pt-2 flex justify-between font-medium">
                  <span className="text-slate-800">Total Cost</span>
                  <span className="text-slate-800">${(deal.cost + 3.5).toFixed(2)}</span>
                </div>
                <div className="mt-3 pt-3 border-t"></div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Sell Price</span>
                  <span className="text-slate-800">${deal.sell.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">- Amazon Referral (15%)</span>
                  <span className="text-red-500">-${(deal.sell * 0.15).toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">- FBA Fee</span>
                  <span className="text-red-500">-$7.35</span>
                </div>
                <div className="border-t pt-2 mt-2 flex justify-between font-bold">
                  <span className="text-emerald-600">💵 Net Profit</span>
                  <span className="text-emerald-600">${deal.profit.toFixed(2)}</span>
                </div>
              </div>
            </div>

            <div className="mt-6 p-4 bg-blue-50 rounded-xl">
              <h4 className="font-medium text-slate-800 mb-3">👥 Supplier Info</h4>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 font-bold text-sm">WK</div>
                <div>
                  <div className="font-medium text-slate-800">{deal.supplier}</div>
                  <div className="text-sm text-slate-500">★★★★☆ (4.2) • Avg Lead Time: 5-7 days</div>
                </div>
              </div>
            </div>

            <div className="mt-6 flex gap-3">
              <button className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors">
                <MessageCircle size={18} />
                Message Supplier
              </button>
              <button className="flex items-center justify-center gap-2 px-4 py-3 border border-slate-200 text-slate-700 rounded-xl font-medium hover:bg-slate-50 transition-colors">
                <Bookmark size={18} />
                Save
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const Dashboard = () => (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Good morning, Sarah! ☀️</h2>
          <p className="text-slate-500">Here's what's happening with your deals today.</p>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard icon={<Inbox size={16} />} label="NEW DEALS" value="47" subtext="since 8am" trend="23%" trendUp={true} />
        <StatCard icon={<Check size={16} />} label="PROFITABLE" value="12" subtext="ready to buy" trend="8%" trendUp={true} />
        <StatCard icon="⏳" label="PENDING" value="8" subtext="need review" trend="12%" trendUp={false} />
        <StatCard icon="💰" label="POTENTIAL" value="$2,340" subtext="est. profit" trend="15%" trendUp={true} />
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-slate-800">🔥 Hot Deals (Act Fast)</h3>
            <button className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1">
              View All <ChevronRight size={16} />
            </button>
          </div>
          <div className="space-y-3">
            {deals.filter(d => d.status === 'profitable').slice(0, 3).map(deal => (
              <div key={deal.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer" onClick={() => setSelectedDeal(deal)}>
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${getStatusColor(deal.status)}`}></div>
                  <div>
                    <div className="font-medium text-slate-800 text-sm">{deal.asin}</div>
                    <div className="text-xs text-slate-500">{deal.title.substring(0, 30)}...</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-medium text-emerald-600">{deal.roi}% ROI</div>
                  <div className="text-xs text-slate-500">${deal.profit.toFixed(2)} profit</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4">📊 Channel Activity</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600">Wholesale Kings</span>
              <div className="flex items-center gap-2">
                <div className="w-24 bg-slate-200 rounded-full h-2">
                  <div className="bg-blue-600 h-2 rounded-full" style={{width: '80%'}}></div>
                </div>
                <span className="text-sm text-slate-800 font-medium">23</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600">Deal Finders</span>
              <div className="flex items-center gap-2">
                <div className="w-24 bg-slate-200 rounded-full h-2">
                  <div className="bg-blue-600 h-2 rounded-full" style={{width: '60%'}}></div>
                </div>
                <span className="text-sm text-slate-800 font-medium">18</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600">Amazon Deals USA</span>
              <div className="flex items-center gap-2">
                <div className="w-24 bg-slate-200 rounded-full h-2">
                  <div className="bg-blue-600 h-2 rounded-full" style={{width: '40%'}}></div>
                </div>
                <span className="text-sm text-slate-800 font-medium">12</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const DealFeed = () => (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-2 text-sm text-emerald-600">
            <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
            Live
          </span>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50">
          <Filter size={16} />
          Filters
        </button>
      </div>

      <div className="flex items-center gap-2 border-b">
        <button className="px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600">All (47)</button>
        <button className="px-4 py-2 text-sm text-slate-500 hover:text-slate-700">🔥 Profitable (12)</button>
        <button className="px-4 py-2 text-sm text-slate-500 hover:text-slate-700">⏳ Pending (8)</button>
        <button className="px-4 py-2 text-sm text-slate-500 hover:text-slate-700">📌 Saved (23)</button>
      </div>

      <div className="space-y-4">
        {deals.map(deal => (
          <DealCard key={deal.id} deal={deal} onClick={setSelectedDeal} />
        ))}
      </div>
    </div>
  );

  const Suppliers = () => (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-slate-500">Manage your supplier relationships</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          + Add Supplier
        </button>
      </div>

      <div className="space-y-4">
        {suppliers.map(supplier => (
          <SupplierCard key={supplier.id} supplier={supplier} />
        ))}
      </div>
    </div>
  );

  const renderContent = () => {
    switch (activeScreen) {
      case 'dashboard': return <Dashboard />;
      case 'dealfeed': return <DealFeed />;
      case 'suppliers': return <Suppliers />;
      default: return (
        <div className="p-6 flex items-center justify-center h-full">
          <div className="text-center text-slate-500">
            <Package size={48} className="mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium">Coming Soon</p>
            <p className="text-sm">This screen is part of the wireframe system</p>
          </div>
        </div>
      );
    }
  };

  return (
    <div className="w-full h-screen bg-slate-50 flex overflow-hidden font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <div className="flex-1 overflow-y-auto">
          {renderContent()}
        </div>
      </div>
      <DealDetailPanel deal={selectedDeal} onClose={() => setSelectedDeal(null)} />
    </div>
  );
}
