import { Skeleton, Box, Card, CardContent } from '@mui/material';

export const DealCardSkeleton = () => (
  <Card>
    <CardContent>
      <Box display="flex" gap={2}>
        <Skeleton variant="rectangular" width={48} height={48} />
        <Box flex={1}>
          <Skeleton variant="text" width="60%" height={24} />
          <Skeleton variant="text" width="40%" height={20} />
          <Box mt={2} display="flex" gap={1}>
            <Skeleton variant="rectangular" width={80} height={24} />
            <Skeleton variant="rectangular" width={80} height={24} />
            <Skeleton variant="rectangular" width={80} height={24} />
          </Box>
        </Box>
      </Box>
    </CardContent>
  </Card>
);

export const StatCardSkeleton = () => (
  <Card>
    <CardContent>
      <Skeleton variant="text" width="40%" height={20} />
      <Skeleton variant="text" width="60%" height={40} />
      <Skeleton variant="text" width="30%" height={16} />
    </CardContent>
  </Card>
);

