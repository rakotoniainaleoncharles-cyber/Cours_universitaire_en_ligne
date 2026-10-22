import { Navigate, Route, Routes } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import AdminDashboard from './pages/admin/AdminDashboard'
import UserManagement from './pages/admin/UserManagement'
import AdminAcademicManagement from './pages/admin/AdminAcademicManagement'
import AdminAuditLog from './pages/admin/AdminAuditLog'
import StudentDashboard from './pages/student/StudentDashboard'
import StudentAssignments from './pages/student/StudentAssignments'
import StudentGrades from './pages/student/StudentGrades'
import StudentCourses from './pages/student/StudentCourses'
import StudentAnnouncements from './pages/student/StudentAnnouncements'
import StudentProfile from './pages/student/StudentProfile'
import TeacherDashboard from './pages/teacher/TeacherDashboard'
import TeacherSubjects from './pages/teacher/TeacherSubjects'
import TeacherStudents from './pages/teacher/TeacherStudents'
import TeacherAssignments from './pages/teacher/TeacherAssignments'
import TeacherAnnouncements from './pages/teacher/TeacherAnnouncements'
import TeacherProfile from './pages/teacher/TeacherProfile'
import { AuthProvider, useAuth } from './context/AuthContext'
import ProtectedRoute from './routes/ProtectedRoute'
import AppShell from './layouts/AppShell'
import { ThemeProvider } from './context/ThemeContext'

function AppContent() {
  const { user, isAuthenticated, loading, authError, refreshUser } = useAuth()

  if (loading) {
    return <div className="loading-screen">Chargement...</div>
  }

  if (authError && !user) {
    return (
      <div className="loading-screen" role="alert">
        <p>{authError}</p>
        <button type="button" className="primary-button" onClick={() => void refreshUser()}>
          Réessayer
        </button>
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/" element={isAuthenticated ? <Navigate to={user?.role === 'admin' ? '/admin' : user?.role === 'teacher' ? '/teacher' : '/student'} replace /> : <LoginPage />} />
      <Route path="/login" element={isAuthenticated ? <Navigate to={user?.role === 'admin' ? '/admin' : user?.role === 'teacher' ? '/teacher' : '/student'} replace /> : <LoginPage />} />

      <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
        <Route element={<AppShell role="admin" />}>
          <Route path="/admin" element={<AdminDashboard section="overview" />} />
          <Route path="/admin/users" element={<UserManagement />} />
          <Route path="/admin/faculties" element={<AdminAcademicManagement section="faculties" />} />
          <Route path="/admin/levels" element={<AdminAcademicManagement section="levels" />} />
          <Route path="/admin/academic-years" element={<AdminAcademicManagement section="years" />} />
          <Route path="/admin/subjects" element={<AdminAcademicManagement section="subjects" />} />
          <Route path="/admin/enrollments" element={<AdminAcademicManagement section="enrollments" />} />
          <Route path="/admin/courses" element={<AdminDashboard section="courses" />} />
          <Route path="/admin/lessons" element={<AdminDashboard section="lessons" />} />
          <Route path="/admin/documents" element={<AdminDashboard section="documents" />} />
          <Route path="/admin/assignments" element={<AdminDashboard section="assignments" />} />
          <Route path="/admin/announcements" element={<AdminDashboard section="announcements" />} />
          <Route path="/admin/activity" element={<AdminAuditLog />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['teacher']} />}>
        <Route element={<AppShell role="teacher" />}>
          <Route path="/teacher" element={<TeacherDashboard section="dashboard" />} />
          <Route path="/teacher/courses" element={<TeacherDashboard section="courses" />} />
          <Route path="/teacher/subjects" element={<TeacherSubjects />} />
          <Route path="/teacher/students" element={<TeacherStudents />} />
          <Route path="/teacher/assignments" element={<TeacherAssignments />} />
          <Route path="/teacher/announcements" element={<TeacherAnnouncements />} />
          <Route path="/teacher/profile" element={<TeacherProfile />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['student']} />}>
        <Route element={<AppShell role="student" />}>
          <Route path="/student" element={<StudentDashboard />} />
          <Route path="/student/courses" element={<StudentCourses />} />
          <Route path="/student/announcements" element={<StudentAnnouncements />} />
          <Route path="/student/assignments" element={<StudentAssignments />} />
          <Route path="/student/grades" element={<StudentGrades />} />
          <Route path="/student/profile" element={<StudentProfile />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeProvider>
  )
}
