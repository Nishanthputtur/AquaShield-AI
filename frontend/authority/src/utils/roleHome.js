export function roleHome(role) {
  switch (role) {
    case 'Administrator':
      return '/admin';
    case 'Engineer':
      return '/engineer';
    case 'Maintenance Officer':
      return '/maintenance';
    case 'Field Inspector':
      return '/inspector';
    case 'Utility Manager':
      return '/manager';
    default:
      return '/login';
  }
}