import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Box, Typography, Chip } from '@mui/material';
import { X } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useSuppliers } from '../../../hooks/useSuppliers';
import { useToast } from '../../../context/ToastContext';
import { habexa } from '../../../theme';

const SupplierFormModal = ({ open, onClose, supplier = null }) => {
  const [name, setName] = useState('');
  const [telegramUsername, setTelegramUsername] = useState('');
  const [whatsappNumber, setWhatsappNumber] = useState('');
  const [email, setEmail] = useState('');
  const [website, setWebsite] = useState('');
  const [notes, setNotes] = useState('');
  const [tags, setTags] = useState([]);
  const [tagInput, setTagInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { createSupplier, updateSupplier, saving } = useSuppliers();
  const { showToast } = useToast();

  const isEditMode = !!supplier;

  useEffect(() => {
    if (supplier) {
      setName(supplier.name || '');
      setTelegramUsername(supplier.telegram_username || '');
      setWhatsappNumber(supplier.whatsapp_number || '');
      setEmail(supplier.email || '');
      setWebsite(supplier.website || '');
      setNotes(supplier.notes || '');
      setTags(supplier.tags || []);
    } else {
      // Reset form for new supplier
      setName('');
      setTelegramUsername('');
      setWhatsappNumber('');
      setEmail('');
      setWebsite('');
      setNotes('');
      setTags([]);
    }
  }, [supplier, open]);

  const handleAddTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!name.trim()) {
      showToast('Supplier name is required', 'error');
      return;
    }

    if (isSubmitting || saving) {
      return; // Prevent double submission
    }

    try {
      setIsSubmitting(true);
      const supplierData = {
        name: name.trim(),
        telegram_username: telegramUsername.trim() || null,
        whatsapp_number: whatsappNumber.trim() || null,
        email: email.trim() || null,
        website: website.trim() || null,
        notes: notes.trim() || null,
        tags: tags.length > 0 ? tags : null,
      };

      if (isEditMode) {
        await updateSupplier(supplier.id, supplierData);
        showToast('Supplier updated successfully', 'success');
      } else {
        await createSupplier(supplierData);
        showToast('Supplier created successfully', 'success');
      }
      
      onClose();
    } catch (error) {
      console.error('Supplier save error:', error);
      showToast(error.message || 'Failed to save supplier', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
        },
      }}
    >
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pb: 2 }}>
        <Typography variant="h6" fontWeight={600}>
          {isEditMode ? 'Edit Supplier' : 'Add New Supplier'}
        </Typography>
        <Button onClick={onClose} sx={{ minWidth: 'auto', p: 1 }}>
          <X size={20} />
        </Button>
      </DialogTitle>

      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Box display="flex" flexDirection="column" gap={3}>
            <TextField
              label="Supplier Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              fullWidth
              disabled={isSubmitting || saving}
            />

            <Box display="flex" gap={2}>
              <TextField
                label="Telegram Username"
                placeholder="@username"
                value={telegramUsername}
                onChange={(e) => setTelegramUsername(e.target.value)}
                fullWidth
                disabled={isSubmitting || saving}
              />
              <TextField
                label="WhatsApp Number"
                placeholder="+1234567890"
                value={whatsappNumber}
                onChange={(e) => setWhatsappNumber(e.target.value)}
                fullWidth
                disabled={isSubmitting || saving}
              />
            </Box>

            <Box display="flex" gap={2}>
              <TextField
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                fullWidth
                disabled={isSubmitting || saving}
              />
              <TextField
                label="Website"
                placeholder="https://..."
                value={website}
                onChange={(e) => setWebsite(e.target.value)}
                fullWidth
                disabled={isSubmitting || saving}
              />
            </Box>

            <Box>
              <TextField
                label="Tags"
                placeholder="Type and press Enter to add"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddTag();
                  }
                }}
                fullWidth
                disabled={isSubmitting || saving}
                helperText="Press Enter to add a tag"
              />
              <Box display="flex" gap={1} flexWrap="wrap" mt={1}>
                {tags.map((tag, index) => (
                  <Chip
                    key={index}
                    label={tag}
                    onDelete={() => handleRemoveTag(tag)}
                    size="small"
                  />
                ))}
              </Box>
            </Box>

            <TextField
              label="Notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              multiline
              rows={4}
              fullWidth
              disabled={isSubmitting || saving}
            />
          </Box>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button onClick={onClose} disabled={isSubmitting || saving}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={isSubmitting || saving || !name.trim()}
            sx={{
              backgroundColor: habexa.purple.main,
              '&:hover': { backgroundColor: habexa.purple.dark },
            }}
          >
            {(isSubmitting || saving) ? 'Saving...' : isEditMode ? 'Update Supplier' : 'Create Supplier'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default SupplierFormModal;

