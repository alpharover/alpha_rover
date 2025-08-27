#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <sensor_msgs/point_cloud2_iterator.hpp>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <algorithm>

class PcReorderNode : public rclcpp::Node {
 public:
  PcReorderNode() : Node("pc_reorder") {
    input_topic_ = declare_parameter<std::string>("input_topic", "/points_in");
    output_topic_ = declare_parameter<std::string>("output_topic", "/points_out");
    out_frame_ = declare_parameter<std::string>("out_frame", "");
    angle_csv_ = declare_parameter<std::string>("angle_csv", "");
    throttle_n_ = declare_parameter<int>("throttle_n", 1);
    qos_depth_ = declare_parameter<int>("qos_depth", 1);

    if (!angle_csv_.empty()) {
      load_angles(angle_csv_);
    }

    auto qos = rclcpp::SensorDataQoS().keep_last(std::max(1, qos_depth_));
    sub_ = create_subscription<sensor_msgs::msg::PointCloud2>(
        input_topic_, qos,
        std::bind(&PcReorderNode::callback, this, std::placeholders::_1));
    pub_ = create_publisher<sensor_msgs::msg::PointCloud2>(output_topic_, qos);

    RCLCPP_INFO(get_logger(), "pc_reorder subscribing %s -> publishing %s; rows=%zu; throttle_n=%d; qos_depth=%d",
                input_topic_.c_str(), output_topic_.c_str(), row_reorder_.size(), throttle_n_, qos_depth_);
  }

 private:
  void load_angles(const std::string &path) {
    std::ifstream f(path);
    if (!f.is_open()) {
      RCLCPP_WARN(get_logger(), "Failed to open angle CSV: %s", path.c_str());
      return;
    }
    std::string line;
    // Expect header line
    if (!std::getline(f, line)) return;
    // Determine column index
    std::vector<std::string> headers;
    split_csv(line, headers);
    int col = -1;
    for (size_t i = 0; i < headers.size(); ++i) {
      auto h = headers[i];
      std::transform(h.begin(), h.end(), h.begin(), ::tolower);
      if (h.find("vertical_angle") != std::string::npos) { col = static_cast<int>(i); break; }
    }
    if (col < 0) {
      RCLCPP_WARN(get_logger(), "No vertical angle column found in %s", path.c_str());
      return;
    }
    std::vector<float> angles;
    while (std::getline(f, line)) {
      std::vector<std::string> cells;
      split_csv(line, cells);
      if (static_cast<int>(cells.size()) <= col) continue;
      try {
        angles.push_back(std::stof(cells[col]));
      } catch (...) {}
    }
    if (angles.empty()) {
      RCLCPP_WARN(get_logger(), "No angles parsed from %s", path.c_str());
      return;
    }
    row_reorder_.resize(angles.size());
    std::iota(row_reorder_.begin(), row_reorder_.end(), 0);
    std::stable_sort(row_reorder_.begin(), row_reorder_.end(), [&](int a, int b){ return angles[a] < angles[b]; });
    RCLCPP_INFO(get_logger(), "Loaded %zu angles; will reorder rows ascending by angle", row_reorder_.size());
  }

  static void split_csv(const std::string &line, std::vector<std::string> &out) {
    out.clear();
    std::istringstream ss(line);
    std::string cell;
    while (std::getline(ss, cell, ',')) out.push_back(cell);
  }

  void callback(const sensor_msgs::msg::PointCloud2::SharedPtr msg) {
    // Throttle publishing if requested
    if (throttle_n_ > 1) {
      if ((++count_ % throttle_n_) != 0) {
        return;
      }
    }
    sensor_msgs::msg::PointCloud2 out;
    out.header = msg->header;
    if (!out_frame_.empty()) out.header.frame_id = out_frame_;
    out.fields = msg->fields;
    out.is_bigendian = msg->is_bigendian;
    out.point_step = msg->point_step;

    const bool can_reorder = (!row_reorder_.empty() && msg->height == row_reorder_.size());
    if (can_reorder) {
      try {
        const size_t row_step = msg->row_step;
        std::vector<uint8_t> buf(row_step * msg->height);
        for (size_t new_row = 0; new_row < row_reorder_.size(); ++new_row) {
          const size_t src_row = static_cast<size_t>(row_reorder_[new_row]);
          const size_t src_off = src_row * row_step;
          const size_t dst_off = new_row * row_step;
          std::copy(msg->data.begin() + src_off, msg->data.begin() + src_off + row_step, buf.begin() + dst_off);
        }
        out.height = msg->height;
        out.width = msg->width;
        out.row_step = msg->row_step;
        out.is_dense = msg->is_dense;
        out.data = std::move(buf);
      } catch (const std::exception &e) {
        RCLCPP_WARN(get_logger(), "Row reorder failed: %s; forwarding original", e.what());
        forward_unmodified(*msg, out);
      }
    } else {
      forward_unmodified(*msg, out);
    }
    pub_->publish(out);
  }

  static void forward_unmodified(const sensor_msgs::msg::PointCloud2 &in, sensor_msgs::msg::PointCloud2 &out) {
    out.height = in.height;
    out.width = in.width;
    out.row_step = in.row_step;
    out.is_dense = in.is_dense;
    out.data = in.data;
  }

  // Params
  std::string input_topic_;
  std::string output_topic_;
  std::string out_frame_;
  std::string angle_csv_;

  // State
  std::vector<int> row_reorder_;
  int throttle_n_ {1};
  int qos_depth_ {1};
  size_t count_ {0};
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr sub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr pub_;
};

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<PcReorderNode>());
  rclcpp::shutdown();
  return 0;
}
