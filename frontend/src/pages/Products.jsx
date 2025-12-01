import { useState } from 'react';
import { Box, Typography, Tabs, Tab, Card, CardContent, Chip, Button, Table, TableBody, TableCell, TableHead, TableRow, IconButton } from '@mui/material';
import { Bookmark, Package, ShoppingCart, Trash2, ExternalLink } from 'lucide-react';
import { useWatchlist } from '../hooks/useWatchlist';
import { useDeals } from '../hooks/useDeals';
import { useOrders } from '../hooks/useOrders';
import { formatCurrency, formatROI, formatRank } from '../utils/formatters';
import EmptyState from '../components/common/EmptyState';
import { useToast } from '../context/ToastContext';
import StatusBadge from '../components/common/StatusBadge';
import { habexa } from '../theme';

const Products = () => {
  const [tab, setTab] = useState(0);
  const { watchlist, loading: watchlistLoading, removeFromWatchlist } = useWatchlist();
  const { deals, loading: dealsLoading } = useDeals({ status: 'analyzed' });
  const { orders, loading: ordersLoading } = useOrders();
  const { showToast } = useToast();

  const handleRemoveFromWatchlist = async (itemId) => {
    try {
      await removeFromWatchlist(itemId);
      showToast('Removed from watchlist', 'success');
    } catch (error) {
      showToast('Failed to remove from watchlist', 'error');
    }
  };

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} mb={4}>
        Products
      </Typography>

      <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label={`📌 Watchlist (${watchlist.length})`} />
        <Tab label={`📊 Analyzed (${deals.length})`} />
        <Tab label={`🛒 Ordered (${orders.length})`} />
      </Tabs>

      {/* Watchlist Tab */}
      {tab === 0 && (
        <>
          {watchlistLoading ? (
            <Typography>Loading...</Typography>
          ) : watchlist.length === 0 ? (
            <EmptyState
              icon={Bookmark}
              title="No items in watchlist"
              message="Save deals to your watchlist to track them here"
            />
          ) : (
            <Box display="flex" flexDirection="column" gap={2}>
              {watchlist.map((item) => (
                <Card key={item.id}>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="start">
                      <Box flex={1}>
                        <Typography variant="h6" fontWeight={600} mb={0.5}>
                          {item.asin}
                        </Typography>
                        {item.target_price && (
                          <Typography variant="body2" color="text.secondary" mb={1}>
                            Target Price: {formatCurrency(item.target_price)}
                          </Typography>
                        )}
                        {item.notes && (
                          <Typography variant="body2" color="text.secondary" mb={1}>
                            {item.notes}
                          </Typography>
                        )}
                        <Box display="flex" gap={1} mt={2}>
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<ExternalLink size={14} />}
                            href={`https://amazon.com/dp/${item.asin}`}
                            target="_blank"
                          >
                            View on Amazon
                          </Button>
                        </Box>
                      </Box>
                      <IconButton
                        onClick={() => handleRemoveFromWatchlist(item.id)}
                        color="error"
                      >
                        <Trash2 size={18} />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              ))}
            </Box>
          )}
        </>
      )}

      {/* Analyzed Tab */}
      {tab === 1 && (
        <>
          {dealsLoading ? (
            <Typography>Loading...</Typography>
          ) : deals.length === 0 ? (
            <EmptyState
              icon={Package}
              title="No analyzed products"
              message="Analyze some ASINs to see them here"
            />
          ) : (
            <Card>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>ASIN</TableCell>
                    <TableCell>Product</TableCell>
                    <TableCell>ROI</TableCell>
                    <TableCell>Profit</TableCell>
                    <TableCell>Rank</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {deals.map((deal) => (
                    <TableRow key={deal.id}>
                      <TableCell>
                        <Typography fontFamily="monospace" fontSize="0.875rem">
                          {deal.asin}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                          {deal.title || 'Unknown Product'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={formatROI(deal.roi)}
                          size="small"
                          sx={{
                            backgroundColor: deal.roi > 0 ? habexa.success.light : habexa.error.light,
                            color: deal.roi > 0 ? habexa.success.main : habexa.error.main,
                            fontWeight: 600,
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          fontWeight={600}
                          color={deal.net_profit > 0 ? 'success.main' : 'error.main'}
                        >
                          {formatCurrency(deal.net_profit)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {formatRank(deal.sales_rank)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={deal.status} roi={deal.roi} />
                      </TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          variant="outlined"
                          href={`https://amazon.com/dp/${deal.asin}`}
                          target="_blank"
                          startIcon={<ExternalLink size={14} />}
                        >
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}
        </>
      )}

      {/* Ordered Tab */}
      {tab === 2 && (
        <>
          {ordersLoading ? (
            <Typography>Loading...</Typography>
          ) : orders.length === 0 ? (
            <EmptyState
              icon={ShoppingCart}
              title="No orders yet"
              message="Orders will appear here when you place them"
            />
          ) : (
            <Box display="flex" flexDirection="column" gap={2}>
              {orders.map((order) => (
                <Card key={order.id}>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="start">
                      <Box flex={1}>
                        <Typography variant="h6" fontWeight={600} mb={0.5}>
                          {order.asin}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" mb={1}>
                          Quantity: {order.quantity} × {formatCurrency(order.unit_cost)} = {formatCurrency(order.total_cost)}
                        </Typography>
                        <Box display="flex" gap={1} mt={1}>
                          <Chip
                            label={order.status}
                            size="small"
                            color={
                              order.status === 'received' ? 'success' :
                              order.status === 'shipped' ? 'info' :
                              order.status === 'confirmed' ? 'primary' :
                              'default'
                            }
                          />
                          {order.suppliers && (
                            <Typography variant="body2" color="text.secondary">
                              Supplier: {order.suppliers.name}
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              ))}
            </Box>
          )}
        </>
      )}
    </Box>
  );
};

export default Products;
