import React from 'react';
import {
  TableRow,
  TableCell,
  Checkbox,
  Box,
  Typography,
  Chip,
  Avatar,
  Link,
  alpha
} from '@mui/material';
import InlineEditCell from './InlineEditCell';
import { formatCurrency, formatPercentage, formatNumber } from '../../utils/formatters';

export default function AnalyzerTableRow({
  product,
  selected,
  visibleColumns,
  profitColor,
  onSelect,
  onFieldUpdate,
  columns = [],
  roiValue = 0
}) {
  const handleFieldUpdate = async (field, value) => {
    if (onFieldUpdate) {
      await onFieldUpdate(product.id, field, value);
    }
  };

  const getCellValue = (columnId) => {
    const value = product[columnId];
    
    // Handle nested values
    if (columnId === 'supplier_name' && product.product_sources?.[0]?.suppliers?.name) {
      return product.product_sources[0].suppliers.name;
    }
    
    if (columnId === 'wholesale_cost' && product.product_sources?.[0]?.wholesale_cost) {
      return product.product_sources[0].wholesale_cost;
    }
    
    if (columnId === 'buy_cost' && product.product_sources?.[0]?.buy_cost) {
      return product.product_sources[0].buy_cost;
    }
    
    if (columnId === 'pack_size' && product.product_sources?.[0]?.pack_size) {
      return product.product_sources[0].pack_size;
    }
    
    if (columnId === 'moq' && product.product_sources?.[0]?.moq) {
      return product.product_sources[0].moq;
    }
    
    if (columnId === 'supplier_sku' && product.product_sources?.[0]?.supplier_sku) {
      return product.product_sources[0].supplier_sku;
    }
    
    return value;
  };

  const renderCell = (column) => {
    const value = getCellValue(column.id);
    const columnConfig = columns.find(c => c.id === column.id) || {};

    // Inline editable fields
    const editableFields = ['wholesale_cost', 'buy_cost', 'pack_size', 'moq'];
    const isEditable = editableFields.includes(column.id);

    switch (column.id) {
      case 'image':
        return (
          <Avatar
            src={product.image_url}
            alt={product.title}
            variant="rounded"
            sx={{ width: 50, height: 50 }}
          >
            {product.title?.[0]?.toUpperCase() || '?'}
          </Avatar>
        );

      case 'asin':
        return (
          <Link
            href={`https://amazon.com/dp/${product.asin}`}
            target="_blank"
            rel="noopener noreferrer"
            sx={{ textDecoration: 'none', color: 'primary.main' }}
          >
            {product.asin}
          </Link>
        );

      case 'title':
        return (
          <Typography variant="body2" sx={{ maxWidth: 300 }}>
            {product.title || '—'}
          </Typography>
        );

      case 'wholesale_cost':
      case 'buy_cost':
        return (
          <InlineEditCell
            value={value || 0}
            type="number"
            min={0}
            step={0.01}
            prefix="$"
            formatValue={(v) => formatCurrency(v)}
            onSave={(newValue) => handleFieldUpdate(column.id, newValue)}
            editable={isEditable}
          />
        );

      case 'pack_size':
      case 'moq':
        return (
          <InlineEditCell
            value={value || 1}
            type="integer"
            min={1}
            formatValue={(v) => formatNumber(v)}
            onSave={(newValue) => handleFieldUpdate(column.id, newValue)}
            editable={isEditable}
          />
        );

      case 'sell_price':
      case 'buy_box_price':
        return formatCurrency(value);

      case 'profit':
      case 'profit_amount':
        return (
          <Typography
            variant="body2"
            sx={{
              color: value >= 0 ? 'success.main' : 'error.main',
              fontWeight: 'bold'
            }}
          >
            {formatCurrency(value)}
          </Typography>
        );

      case 'roi':
      case 'roi_percentage':
        return (
          <Typography
            variant="body2"
            sx={{
              color: profitColor,
              fontWeight: 'bold'
            }}
          >
            {formatPercentage(value)}
          </Typography>
        );

      case 'margin':
      case 'margin_percentage':
        return formatPercentage(value);

      case 'profit_tier':
        const tierColors = {
          excellent: 'success',
          good: 'info',
          marginal: 'warning',
          unprofitable: 'error'
        };
        return (
          <Chip
            label={value || '—'}
            size="small"
            color={tierColors[value?.toLowerCase()] || 'default'}
            sx={{ textTransform: 'capitalize' }}
          />
        );

      case 'is_profitable':
        return (
          <Chip
            label={value ? 'Yes' : 'No'}
            size="small"
            color={value ? 'success' : 'default'}
          />
        );

      case 'in_stock':
      case 'amazon_in_stock':
        return (
          <Chip
            label={value ? 'In Stock' : 'Out of Stock'}
            size="small"
            color={value ? 'success' : 'default'}
          />
        );

      case 'has_promo':
        return value ? (
          <Chip label="Promo" size="small" color="warning" />
        ) : (
          '—'
        );

      case 'bsr':
      case 'current_sales_rank':
        return value ? `#${formatNumber(value)}` : '—';

      case 'fba_sellers':
      case 'fba_seller_count':
        return formatNumber(value || 0);

      case 'est_monthly_sales':
        return formatNumber(value || 0);

      case 'bought_last_30d':
      case 'bought_last_60d':
      case 'bought_last_90d':
        const boughtValue = value || 0;
        return (
          <Typography
            variant="body2"
            sx={{
              color: boughtValue > 0 ? 'success.main' : 'text.secondary',
              fontWeight: boughtValue > 0 ? 600 : 400
            }}
          >
            {formatNumber(boughtValue)}
          </Typography>
        );

      default:
        // Default rendering
        if (typeof value === 'boolean') {
          return value ? 'Yes' : 'No';
        }
        if (typeof value === 'number') {
          return formatNumber(value);
        }
        return value ?? '—';
    }
  };

  // Get row background color based on ROI tier
  const getRowBgColor = () => {
    if (selected) {
      return alpha(profitColor || '#1976d2', 0.1);
    }
    
    // Color code by ROI tier
    if (roiValue >= 50) return alpha('#4caf50', 0.08); // Excellent - light green
    if (roiValue >= 30) return alpha('#ff9800', 0.06); // Good - light orange
    if (roiValue >= 15) return alpha('#ffc107', 0.05); // Acceptable - light yellow
    if (roiValue >= 5) return alpha('#ff9800', 0.04); // Marginal - very light orange
    if (roiValue < 5 && roiValue > -100) return alpha('#f44336', 0.05); // Unprofitable - light red
    
    return 'transparent';
  };

  return (
    <TableRow
      sx={{
        bgcolor: getRowBgColor(),
        '&:hover': {
          bgcolor: alpha(profitColor || '#1976d2', 0.1),
          cursor: 'pointer'
        },
        transition: 'background-color 0.2s ease'
      }}
    >
      {/* Checkbox - STICKY */}
      <TableCell 
        padding="checkbox"
        sx={{ 
          position: 'sticky', 
          left: 0, 
          bgcolor: 'inherit', 
          zIndex: 1,
          minWidth: 48
        }}
      >
        <Checkbox
          checked={selected}
          onChange={(e) => onSelect(e.target.checked)}
        />
      </TableCell>

      {/* Image (Sticky) */}
      <TableCell
        sx={{
          position: 'sticky',
          left: 48,
          zIndex: 1,
          bgcolor: selected ? alpha(profitColor || '#1976d2', 0.1) : 'background.paper'
        }}
      >
        {renderCell({ id: 'image' })}
      </TableCell>

      {/* ASIN (Sticky) */}
      <TableCell
        sx={{
          position: 'sticky',
          left: 148,
          zIndex: 1,
          bgcolor: selected ? alpha(profitColor || '#1976d2', 0.1) : 'background.paper'
        }}
      >
        {renderCell({ id: 'asin' })}
      </TableCell>

      {/* Dynamic Columns */}
      {columns
        .filter(col => visibleColumns.includes(col.id) && !['select', 'image', 'asin'].includes(col.id))
        .map(column => {
          const isEditable = column.editable && ['wholesale_cost', 'buy_cost', 'pack_size', 'moq', 'supplier_sku'].includes(column.id);
          
          return (
            <TableCell key={column.id} sx={{ minWidth: column.width || 120 }}>
              {isEditable ? (
                <InlineEditCell
                  value={getCellValue(column.id)}
                  onSave={(newValue) => onFieldUpdate(column.id, newValue)}
                  type={column.type === 'currency' ? 'number' : column.type === 'number' ? 'number' : 'text'}
                  formatValue={(v) => {
                    if (column.type === 'currency') return `$${Number(v).toFixed(2)}`;
                    if (column.type === 'number') return formatNumber(v);
                    return v;
                  }}
                  prefix={column.type === 'currency' ? '$' : undefined}
                  min={column.type === 'number' ? 0 : undefined}
                  step={column.type === 'currency' ? 0.01 : 1}
                />
              ) : (
                renderCell(column)
              )}
            </TableCell>
          );
        })}
    </TableRow>
  );
}

