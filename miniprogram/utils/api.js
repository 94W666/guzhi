// utils/api.js — 后端 API 请求封装
// 本地开发：wx.request 连 localhost:8000
// 云托管上线：wx.cloud.callContainer 免域名免备案

const app = getApp();

function get(path) {
  const useCloud = app.globalData.useCloud;
  if (useCloud) {
    return _callContainer(path);
  }
  return _wxRequest(path);
}

function _wxRequest(path) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: app.globalData.apiBase + path,
      method: "GET",
      timeout: 30000,
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.data);
        } else {
          reject(new Error("HTTP " + res.statusCode));
        }
      },
      fail(err) { reject(err); }
    });
  });
}

function _callContainer(path) {
  return new Promise((resolve, reject) => {
    wx.cloud.callContainer({
      config: { env: app.globalData.cloudEnv },
      path: path,
      method: "GET",
      header: { "X-WX-SERVICE": app.globalData.cloudService },
      timeout: 30000,
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.data);
        } else {
          reject(new Error("HTTP " + res.statusCode));
        }
      },
      fail(err) { reject(err); }
    });
  });
}

module.exports = { get };
