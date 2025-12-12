import React, { useState, useEffect } from 'react';
import { Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography, Box, Button, Chip, TextField, InputAdornment } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';

export default function SupplierProductsTab({ supplierId }) {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => { fetchProducts(); }, [supplierId]);

  const fetchProducts = async () => {
    try {
      const response = await api.get(`/products?supplier_id=${supplierId}`);
      setProducts(response.data?.products || response.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = products.filter(p => 
    p.title?.toLowerCase().includes(search.toLowerCase()) || 
    p.asin?.toLowerCase().includes(search.toLowerCase())
  );

  const getProfitColor = (roi) => {
    if (roi >= 50) return 'success';
    if (roi >= 30) return 'info';
    if (roi >= 15) return 'warning';
    return 'error';
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Box display="flex" justifyContent="space-between" mb={2}>
        <Typography variant="h6" fontWeight="bold">Products ({products.length})</Typography>
        <Box display="flex" gap={2}>
          <TextField 
            placeholder="Search..." 
            value={search} 
            onChange={(e) => setSearch(e.target.value)} 
            size="small"
            InputProps={{ 
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              )
            }} 
          />
          <Button 
            variant="contained" 
            startIcon={<AddIcon />} 
            onClick={() => navigate(`/products/new?supplier=${supplierId}`)}
          >
            Add Product
          </Button>
        </Box>
      </Box>

      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Image</TableCell>
              <TableCell>ASIN</TableCell>
              <TableCell>Title</TableCell>
              <TableCell>Pack</TableCell>
              <TableCell>Cost</TableCell>
              <TableCell>Profit</TableCell>
              <TableCell>ROI</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8} align="center">Loading...</TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center">No products found</TableCell>
              </TableRow>
            ) : (
              filtered.map(p => (
                <TableRow 
                  key={p.id} 
                  hover 
                  onClick={() => navigate(`/products/${p.id}`)} 
                  sx={{ cursor: 'pointer' }}
                >
                  <TableCell>
                    {p.image_url ? (
                      <img 
                        src={p.image_url} 
                        alt={p.title} 
                        style={{ width: 50, height: 50, objectFit: 'contain' }} 
                      />
                    ) : (
                      <Box sx={{ width: 50, height: 50, bgcolor: 'grey.200' }} />
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      {p.asin || 'PENDING'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                      {p.title || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>{p.pack_size || p.product_sources?.[0]?.pack_size || 1}</TableCell>
                  <TableCell>
                    ${(p.wholesale_cost || p.product_sources?.[0]?.wholesale_cost || 0).toFixed(2)}
                  </TableCell>
                  <TableCell>
                    <Typography 
                      variant="body2" 
                      fontWeight="bold" 
                      color={(p.profit || p.profit_amount || 0) >= 0 ? 'success.main' : 'error.main'}
                    >
                      ${(p.profit || p.profit_amount || 0).toFixed(2)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={`${(p.roi || p.roi_percentage || 0).toFixed(0)}%`} 
                      color={getProfitColor(p.roi || p.roi_percentage || 0)} 
                      size="small" 
                    />
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={p.in_stock || p.amazon_in_stock ? 'In Stock' : 'Out'} 
                      color={p.in_stock || p.amazon_in_stock ? 'success' : 'default'} 
                      size="small" 
                      variant="outlined" 
                    />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}

