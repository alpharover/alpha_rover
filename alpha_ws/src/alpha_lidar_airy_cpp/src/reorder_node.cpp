#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <diagnostic_msgs/msg/diagnostic_array.hpp>
#include <diagnostic_msgs/msg/diagnostic_status.hpp>
#include <yaml-cpp/yaml.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <memory>
#include <numeric>
#include <optional>
#include <string>
#include <utility>
#include <vector>
#include <sstream>

using std::placeholders::_1;
using namespace std::chrono_literals;

namespace {

struct Config {
  bool reorder_enabled{true};
  int expected_h{96};
  int expected_w{900};
  std::string angle_table_path; // optional
};

static std::optional<Config> load_config(const std::string & path) {
  try {
    YAML::Node root = YAML::LoadFile(path);
    Config cfg;
    if (root["reorder_enabled"]) cfg.reorder_enabled = root["reorder_enabled"].as<bool>();
    if (root["expected_dims"]) {
      auto d = root["expected_dims"];
      if (d["height"]) cfg.expected_h = d["height"].as<int>();
      if (d["width"]) cfg.expected_w = d["width"].as<int>();
    }
    if (root["vertical_angle_table_path"]) cfg.angle_table_path = root["vertical_angle_table_path"].as<std::string>();
    return cfg;
  } catch (...) {
    return std::nullopt;
  }
}

static std::vector<double> read_angles(const std::string & csv_path) {
  std::vector<double> v;
  std::ifstream f(csv_path);
  if (!f.good()) return v;
  std::string line;
  bool header_checked = false;
  bool has_header = false;
  while (std::getline(f, line)) {
    if (!header_checked) {
      header_checked = true;
      // detect header if first token is non-numeric
      try {
        size_t i = 0; (void)i;
        std::stod(line, &i);
        // numeric: no header
      } catch (...) {
        has_header = true;
        continue;
      }
    }
    // take first column
    size_t comma = line.find(',');
    std::string tok = (comma == std::string::npos) ? line : line.substr(0, comma);
    try {
      v.push_back(std::stod(tok));
    } catch (...) {
      continue;
    }
  }
  return v;
}

inline uint64_t now_ns(rclcpp::Clock & clock) { return static_cast<uint64_t>(clock.now().nanoseconds()); }

struct ReorderState {
  std::vector<int> row_order; // sorted indices by angle
  bool have_order{false};
  std::string angle_hash;
};

class ReorderNodeCpp : public rclcpp::Node {
public:
  ReorderNodeCpp() : Node("reorder_node_cpp") {
    // Parameters
    config_path_ = declare_parameter<std::string>("config", "alpha_configs/lidar_airy.yaml");
    in_front_ = declare_parameter<std::string>("input_front_topic", "/alpha/lidar/front/points_raw");
    in_rear_  = declare_parameter<std::string>("input_rear_topic",  "/alpha/lidar/rear/points_raw");
    ts_policy_ = declare_parameter<std::string>("timestamp_policy", "sensor");

    auto cfg_opt = load_config(config_path_);
    if (cfg_opt) {
      cfg_ = *cfg_opt;
    }
    // Resolve angle table relative to config
    if (!cfg_.angle_table_path.empty() && cfg_.angle_table_path[0] != '/') {
      auto pos = config_path_.find_last_of("/");
      if (pos != std::string::npos) {
        cfg_.angle_table_path = config_path_.substr(0, pos + 1) + cfg_.angle_table_path;
      }
    }
    if (!cfg_.angle_table_path.empty()) {
      auto ang = read_angles(cfg_.angle_table_path);
      if (!ang.empty()) {
        state_.row_order.resize(static_cast<size_t>(ang.size()));
        std::iota(state_.row_order.begin(), state_.row_order.end(), 0);
        std::stable_sort(state_.row_order.begin(), state_.row_order.end(), [&](int a, int b){ return ang[a] < ang[b]; });
        state_.have_order = true;
        // FNV-1a 64-bit hash of angle bytes (strict-aliasing safe)
        uint64_t h = 1469598103934665603ULL;
        for (double d : ang) {
          unsigned char bytes[sizeof(double)];
          std::memcpy(bytes, &d, sizeof(double));
          for (size_t i = 0; i < sizeof(double); ++i) {
            h ^= static_cast<uint64_t>(bytes[i]);
            h *= 1099511628211ULL;
          }
        }
        std::ostringstream oss; oss << std::hex << h;
        state_.angle_hash = oss.str();
      }
    }

    RCLCPP_INFO(get_logger(), "Reorder C++ ready (expected=%dx%d, order=%s, ts_policy=%s)",
      cfg_.expected_h, cfg_.expected_w, state_.have_order ? "yes" : "no", ts_policy_.c_str());

    auto qos = rclcpp::SensorDataQoS();
    pub_front_ = this->create_publisher<sensor_msgs::msg::PointCloud2>("/alpha/lidar/front/points", qos);
    pub_rear_  = this->create_publisher<sensor_msgs::msg::PointCloud2>("/alpha/lidar/rear/points", qos);
    sub_front_ = this->create_subscription<sensor_msgs::msg::PointCloud2>(in_front_, qos, std::bind(&ReorderNodeCpp::on_front, this, _1));
    sub_rear_  = this->create_subscription<sensor_msgs::msg::PointCloud2>(in_rear_,  qos, std::bind(&ReorderNodeCpp::on_rear,  this, _1));

    diag_pub_ = this->create_publisher<diagnostic_msgs::msg::DiagnosticArray>("/diagnostics", 10);
    diag_timer_ = this->create_wall_timer(1s, std::bind(&ReorderNodeCpp::publish_diag, this));
  }

private:
  void on_front(const sensor_msgs::msg::PointCloud2::SharedPtr msg) { process_and_publish(*msg, *pub_front_, last_front_lat_ms_, rate_front_, true); }
  void on_rear (const sensor_msgs::msg::PointCloud2::SharedPtr msg) { process_and_publish(*msg, *pub_rear_,  last_rear_lat_ms_,  rate_rear_,  false); }

  void process_and_publish(const sensor_msgs::msg::PointCloud2 & in,
                           rclcpp::Publisher<sensor_msgs::msg::PointCloud2> & pub,
                           std::vector<double> & lat_hist_ms,
                           std::vector<double> & rate_hist,
                           bool is_front) {
    const auto t0 = now_ns(*get_clock());
    sensor_msgs::msg::PointCloud2 out;
    out.header = in.header;
    out.fields = in.fields;
    out.is_bigendian = in.is_bigendian;
    out.point_step = in.point_step;
    out.is_dense = false;

    const uint32_t step = in.point_step;
    const uint32_t src_row_step = in.row_step;
    uint32_t h = in.height;
    uint32_t w = in.width;
    std::vector<uint8_t> data(in.data.begin(), in.data.end());

    // Transpose if needed (900x96 -> 96x900)
    if ((h == static_cast<uint32_t>(cfg_.expected_w) && w == static_cast<uint32_t>(cfg_.expected_h)) ||
        (w == static_cast<uint32_t>(cfg_.expected_h) && h > w)) {
      const uint32_t new_h = static_cast<uint32_t>(cfg_.expected_h);
      const uint32_t new_w = static_cast<uint32_t>(cfg_.expected_w);
      const uint32_t new_row_step = step * new_w;
      std::vector<uint8_t> new_bytes(new_row_step * new_h);
      for (uint32_t r = 0; r < new_h; ++r) {
        for (uint32_t c = 0; c < new_w; ++c) {
          size_t src_off = static_cast<size_t>(c) * src_row_step + static_cast<size_t>(r) * step;
          size_t dst_off = static_cast<size_t>(r) * new_row_step + static_cast<size_t>(c) * step;
          std::memcpy(&new_bytes[dst_off], &data[src_off], step);
        }
      }
      data.swap(new_bytes);
      h = new_h; w = new_w;
    }

    // Row reorder by precomputed order
    if (cfg_.reorder_enabled && state_.have_order && state_.row_order.size() == h) {
      const uint32_t row_step = step * w;
      std::vector<uint8_t> new_bytes(row_step * h);
      for (uint32_t dest = 0; dest < h; ++dest) {
        uint32_t src = static_cast<uint32_t>(state_.row_order[dest]);
        if (src >= h) continue;
        std::memcpy(&new_bytes[static_cast<size_t>(dest) * row_step], &data[static_cast<size_t>(src) * row_step], row_step);
      }
      data.swap(new_bytes);
    }

    // Normalize dims to exact expected (pad/truncate)
    const uint32_t target_h = static_cast<uint32_t>(cfg_.expected_h);
    const uint32_t target_w = static_cast<uint32_t>(cfg_.expected_w);
    bool padded = false;
    if (h != target_h || w != target_w) {
      const uint32_t row_step_in  = step * w;
      const uint32_t row_step_out = step * target_w;
      std::vector<uint8_t> new_bytes(row_step_out * target_h, 0);
      const uint32_t rows = std::min(h, target_h);
      const uint32_t cols = std::min(w, target_w);
      for (uint32_t r = 0; r < rows; ++r) {
        std::memcpy(&new_bytes[static_cast<size_t>(r) * row_step_out], &data[static_cast<size_t>(r) * row_step_in], static_cast<size_t>(cols) * step);
      }
      data.swap(new_bytes);
      h = target_h; w = target_w;
      padded = (target_h > rows) || (target_w > cols);
    }

    out.height = h;
    out.width  = w;
    out.row_step = step * w;
    out.data = std::move(data);

    // Timestamp policy
    if (ts_policy_ == "node") {
      out.header.stamp = get_clock()->now();
    }

    pub.publish(out);

    // Metrics
    const auto t1 = now_ns(*get_clock());
    const double ms = static_cast<double>(t1 - t0) / 1e6;
    lat_hist_ms.push_back(ms);
    // Keep ~10s worth at 20 Hz max
    if (lat_hist_ms.size() > 200) lat_hist_ms.erase(lat_hist_ms.begin(), lat_hist_ms.begin() + (lat_hist_ms.size() - 200));
    rate_hist.push_back(static_cast<double>(t1) / 1e9);
    while (rate_hist.size() > 2 && (rate_hist.back() - rate_hist.front()) > 10.0) rate_hist.erase(rate_hist.begin());
    if (padded) {
      if (is_front) ++pad_front_count_; else ++pad_rear_count_;
    }
  }

  static std::pair<double,double> p50p95(const std::vector<double> & v) {
    if (v.empty()) return {0.0, 0.0};
    std::vector<double> s = v;
    std::sort(s.begin(), s.end());
    auto pick = [&](double p){ size_t idx = std::min(s.size()-1, static_cast<size_t>(std::round(p * (s.size()-1)))); return s[idx]; };
    return {pick(0.50), pick(0.95)};
  }

  static double rate_hz(const std::vector<double> & ts) {
    if (ts.size() < 2) return 0.0;
    double dur = ts.back() - ts.front();
    return dur > 0.0 ? (ts.size()-1) / dur : 0.0;
  }

  void publish_diag() {
    auto [p50f, p95f] = p50p95(last_front_lat_ms_);
    auto [p50r, p95r] = p50p95(last_rear_lat_ms_);
    double rf = rate_hz(rate_front_);
    double rr = rate_hz(rate_rear_);

    diagnostic_msgs::msg::DiagnosticStatus st;
    st.level = diagnostic_msgs::msg::DiagnosticStatus::OK;
    st.name = "alpha_lidar_airy/reorder";
    st.message = "reorder metrics";
    auto kv = [](const std::string & k, const std::string & v){ diagnostic_msgs::msg::KeyValue kv; kv.key = k; kv.value = v; return kv; };
    st.values.push_back(kv("reorder_backend", "cpp"));
    if (!state_.angle_hash.empty()) st.values.push_back(kv("angle_table_hash", state_.angle_hash));
    st.values.push_back(kv("reorder_latency_ms.front.p50", std::to_string(p50f)));
    st.values.push_back(kv("reorder_latency_ms.front.p95", std::to_string(p95f)));
    st.values.push_back(kv("reorder_latency_ms.rear.p50",  std::to_string(p50r)));
    st.values.push_back(kv("reorder_latency_ms.rear.p95",  std::to_string(p95r)));
    st.values.push_back(kv("points_rate_hz.front", std::to_string(rf)));
    st.values.push_back(kv("points_rate_hz.rear",  std::to_string(rr)));
    st.values.push_back(kv("dropped_or_padded_frames.front", std::to_string(pad_front_count_)));
    st.values.push_back(kv("dropped_or_padded_frames.rear", std::to_string(pad_rear_count_)));

    diagnostic_msgs::msg::DiagnosticArray arr;
    arr.status.push_back(st);
    diag_pub_->publish(arr);
  }

  // Params
  std::string config_path_;
  std::string in_front_;
  std::string in_rear_;
  std::string ts_policy_;
  Config cfg_{};
  ReorderState state_{};

  // IO
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr pub_front_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr pub_rear_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr sub_front_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr sub_rear_;
  rclcpp::Publisher<diagnostic_msgs::msg::DiagnosticArray>::SharedPtr diag_pub_;
  rclcpp::TimerBase::SharedPtr diag_timer_;

  // Metrics
  std::vector<double> last_front_lat_ms_;
  std::vector<double> last_rear_lat_ms_;
  std::vector<double> rate_front_;
  std::vector<double> rate_rear_;
  uint64_t pad_front_count_{0};
  uint64_t pad_rear_count_{0};
};

} // namespace

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<ReorderNodeCpp>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
