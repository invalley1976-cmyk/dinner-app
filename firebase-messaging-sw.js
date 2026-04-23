// Firebase Cloud Messaging Service Worker
// バックグラウンドでpush通知を受け取るためのWorker
importScripts("https://www.gstatic.com/firebasejs/10.14.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.14.0/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "AIzaSyAKcQ-qTA3KCIWUV1N2TZWahhVEaWn_mlI",
  authDomain: "dinner-app-dd27f.firebaseapp.com",
  projectId: "dinner-app-dd27f",
  storageBucket: "dinner-app-dd27f.firebasestorage.app",
  messagingSenderId: "1030430671207",
  appId: "1:1030430671207:web:2e6b42bedd0bbd1e946fc2"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const title = payload?.notification?.title || '晩ごはん';
  const options = {
    body: payload?.notification?.body || '',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    tag: 'dinner-app-' + (payload?.data?.type || 'msg'),
    renotify: true
  };
  self.registration.showNotification(title, options);
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((wins) => {
      for (const c of wins) {
        if (c.url.includes('/dinner-app/') && 'focus' in c) return c.focus();
      }
      if (clients.openWindow) return clients.openWindow('/dinner-app/');
    })
  );
});
