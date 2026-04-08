// ============================================
// Realistic MongoDB data with performance problems
// Intentionally missing indexes for the MCP server to find
// ============================================

db = db.getSiblingDB('appdb');

// Create user for the app
db.createUser({
  user: 'appuser',
  pwd: 'appuser123',
  roles: [{ role: 'readWrite', db: 'appdb' }]
});

// --- Users collection: no index on email (common lookup field) ---
var users = [];
var countries = ['US', 'MX', 'BR', 'AR', 'CO', 'CL', 'PE'];
for (var i = 0; i < 10000; i++) {
  users.push({
    email: 'user' + i + '@example.com',
    name: 'User ' + i,
    country: countries[i % countries.length],
    age: 18 + (i % 60),
    plan: ['free', 'basic', 'premium'][i % 3],
    tags: ['active', 'verified', 'newsletter'].slice(0, (i % 3) + 1),
    created_at: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000)
  });
}
db.users.insertMany(users);

// --- Events collection: high volume, no indexes at all ---
var events = [];
var eventTypes = ['page_view', 'click', 'purchase', 'signup', 'logout'];
for (var i = 0; i < 50000; i++) {
  events.push({
    user_id: 'user' + Math.floor(Math.random() * 10000),
    type: eventTypes[i % eventTypes.length],
    metadata: {
      page: '/page/' + (i % 100),
      duration_ms: Math.floor(Math.random() * 5000),
      device: ['mobile', 'desktop', 'tablet'][i % 3]
    },
    timestamp: new Date(Date.now() - Math.random() * 90 * 24 * 60 * 60 * 1000)
  });
}
db.events.insertMany(events);

// --- Products collection: only _id index, queries on category + price ---
var products = [];
var categories = ['electronics', 'clothing', 'food', 'books', 'toys'];
for (var i = 0; i < 5000; i++) {
  products.push({
    name: 'Product ' + i,
    category: categories[i % categories.length],
    price: Math.round(Math.random() * 500 * 100) / 100,
    rating: Math.round(Math.random() * 5 * 10) / 10,
    in_stock: Math.random() > 0.2,
    created_at: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000)
  });
}
db.products.insertMany(products);

// Enable profiling to capture slow operations
db.setProfilingLevel(2, { slowms: 100 });

// Run some queries to populate the profiler (intentionally slow)
db.users.find({ email: 'user5000@example.com' }).toArray();
db.events.find({ type: 'purchase', 'metadata.device': 'mobile' }).sort({ timestamp: -1 }).toArray();
db.products.find({ category: 'electronics', price: { $gt: 100, $lt: 200 } }).toArray();
db.events.aggregate([
  { $match: { type: 'purchase' } },
  { $group: { _id: '$user_id', total: { $sum: 1 } } },
  { $sort: { total: -1 } },
  { $limit: 10 }
]).toArray();
