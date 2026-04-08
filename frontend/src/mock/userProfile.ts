export interface MockUserProfile {
  uid: string;
  username: string;
  avatarUrl: string;
  bio: string;
}

// Bilibili profile mock for demo rendering.
export const mockUserProfile: MockUserProfile = {
  uid: "354312859",
  username: "天鹅",
  avatarUrl: "/avatar.jpg",
  bio: "面试题训练进行中"
};

