import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const routes = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/Login.vue"),
    meta: { requiresAuth: false },
  },
  {
    path: "/",
    component: () => import("@/layouts/MainLayout.vue"),
    redirect: "/chat",
    meta: { requiresAuth: true },
    children: [
      {
        path: "chat",
        name: "Chat",
        component: () => import("@/views/Chat.vue"),
        meta: { title: "智能问答" },
      },
      {
        path: "users",
        name: "Users",
        component: () => import("@/views/Users.vue"),
        meta: { title: "用户管理", requiresRole: [0, 1] }, // 管理员和教师
      },
      {
        path: "documents",
        name: "Documents",
        component: () => import("@/views/Documents.vue"),
        meta: { title: "文档管理" },
      },
      {
        path: "courses",
        name: "Courses",
        component: () => import("@/views/Courses.vue"),
        meta: { title: "课程管理" },
      },
      {
        path: "courses/:id",
        name: "CourseDetail",
        component: () => import("@/views/CourseDetail.vue"),
        meta: { title: "课程详情" },
      },
      {
        path: "assignments",
        name: "Assignments",
        component: () => import("@/views/AssignmentList.vue"),
        meta: { title: "作业管理" },
      },
      {
        path: "assignments/create",
        name: "AssignmentCreate",
        component: () => import("@/views/AssignmentCreate.vue"),
        meta: { title: "创建作业", requiresRole: [0, 1] },
      },
      {
        path: "assignments/:id",
        name: "AssignmentDetail",
        component: () => import("@/views/AssignmentDetail.vue"),
        meta: { title: "作业详情" },
      },
      {
        path: "assignments/:id/edit",
        name: "AssignmentEdit",
        component: () => import("@/views/AssignmentEdit.vue"),
        meta: { title: "编辑作业", requiresRole: [0, 1] },
      },
      {
        path: "assignments/:id/submissions",
        name: "SubmissionList",
        component: () => import("@/views/SubmissionList.vue"),
        meta: { title: "提交列表", requiresRole: [0, 1] },
      },
      {
        path: "assignments/:id/grade-report",
        name: "GradeReport",
        component: () => import("@/views/GradeReport.vue"),
        meta: { title: "评分报告" },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();

  // 检查是否需要登录
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    next("/login");
    return;
  }

  // 如果已登录，访问登录页则跳转到主页
  if (to.path === "/login" && authStore.isLoggedIn) {
    next("/");
    return;
  }

  // 检查角色权限
  if (to.meta.requiresRole) {
    const userType = authStore.userType;
    if (!to.meta.requiresRole.includes(userType)) {
      // 学生不能访问用户管理页面
      next("/chat");
      return;
    }
  }

  next();
});

export default router;
