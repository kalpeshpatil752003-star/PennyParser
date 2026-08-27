import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { ProtectedRoute } from '../auth/ProtectedRoute';
import { DocumentsPage } from '../features/documents/pages/DocumentsPage';
import { DocumentDetailPage } from '../features/documents/pages/DocumentDetailPage';
import { ResearchPage } from '../features/research/pages/ResearchPage';
import { AnalysisPage } from '../features/analysis/pages/AnalysisPage';

// Auth pages
import { LoginPage } from '../features/auth/pages/LoginPage';
import { RegisterPage } from '../features/auth/pages/RegisterPage';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    element: <ProtectedRoute />, // All routes below here require login!
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: '/', element: <Navigate to="/documents" replace /> },
          { path: '/documents', element: <DocumentsPage /> },
          { path: '/documents/:id', element: <DocumentDetailPage /> },
          { path: '/research', element: <ResearchPage /> },
          { path: '/research/:chatId', element: <ResearchPage /> },
          { path: '/analysis', element: <AnalysisPage /> },
        ],
      },
    ],
  },
]);