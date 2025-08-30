// Mapping node that loads provider config and subscribes to LiDAR clouds.
// Currently uses a DummyProvider that implements IMappingProvider.

#include <memory>
#include <string>
#include <vector>
#include <fstream>

#include <pluginlib/class_loader.hpp>
#include <std_msgs/msg/string.hpp>

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>

#include "alpha_mapping/provider_interface.hpp"

using sensor_msgs::msg::PointCloud2;

namespace alpha_mapping {

class DummyProvider : public IMappingProvider {
public:
  bool configure(rclcpp::Node* node) override {
    (void)node;
    return true;
  }
  void integrateCloud(const std::shared_ptr<PointCloud2>&, const std::string&, const rclcpp::Time&) override {
    // no-op
  }
  void reset() override {}
};

class MappingNode : public rclcpp::Node {
public:
  MappingNode() : rclcpp::Node("alpha_mapping_node") {
    this->declare_parameter<std::string>("config", "alpha_configs/mapping_provider.yaml");
    this->declare_parameter<std::string>("provider_plugin", "alpha_mapping/NvbloxProvider");
    auto cfg_path = this->get_parameter("config").as_string();
    // Minimal YAML parsing: look for lines 'provider:' and 'input_topics:'
    std::string provider = "nvblox";
    std::vector<std::string> topics;
    std::ifstream f(cfg_path);
    if (f.good()) {
      std::string line;
      while (std::getline(f, line)) {
        if (line.find("provider:") != std::string::npos) {
          auto pos = line.find(":");
          if (pos != std::string::npos) {
            provider = std::string(line.begin() + static_cast<long>(pos + 1), line.end());
            // trim spaces
            provider.erase(0, provider.find_first_not_of(" \t"));
          }
        }
        if (line.find("input_topics:") != std::string::npos) {
          // Next line(s) expected YAML list [a, b] or on same line
          auto pos = line.find("[");
          std::string rest = line;
          if (pos == std::string::npos) {
            // try next line
            std::string next;
            if (std::getline(f, next)) rest = next;
            pos = rest.find("[");
          }
          if (pos != std::string::npos) {
            auto end = rest.find("]", pos);
            if (end != std::string::npos) {
              auto inner = rest.substr(pos + 1, end - pos - 1);
              // split by comma
              size_t s = 0;
              while (s < inner.size()) {
                auto c = inner.find(',', s);
                auto token = inner.substr(s, (c == std::string::npos ? inner.size() : c) - s);
                // trim
                auto start = token.find_first_not_of(" \t");
                auto stop = token.find_last_not_of(" \t");
                if (start != std::string::npos) {
                  std::string t = token.substr(start, stop - start + 1);
                  topics.push_back(t);
                }
                if (c == std::string::npos) break;
                s = c + 1;
              }
            }
          }
        }
      }
    }
    if (topics.empty()) {
      topics = {"/alpha/lidar/front/points", "/alpha/lidar/rear/points"};
    }

    // Load provider via pluginlib if available; fallback to DummyProvider
    std::string plugin_name = this->get_parameter("provider_plugin").as_string();
    try {
      loader_ = std::make_shared<pluginlib::ClassLoader<IMappingProvider>>("alpha_mapping", "alpha_mapping::IMappingProvider");
      provider_.reset(loader_->createSharedInstance(plugin_name));
      provider_->configure(this);
      RCLCPP_INFO(this->get_logger(), "Loaded provider plugin: %s", plugin_name.c_str());
    } catch (const std::exception &e) {
      RCLCPP_WARN(this->get_logger(), "Failed to load provider plugin '%s': %s. Using DummyProvider.", plugin_name.c_str(), e.what());
      provider_.reset(new DummyProvider());
      provider_->configure(this);
    }

    // Subscribe
    for (const auto & t : topics) {
      auto sub = this->create_subscription<PointCloud2>(t, 10, [this, t](PointCloud2::SharedPtr msg) {
        provider_->integrateCloud(msg, msg->header.frame_id, rclcpp::Time(msg->header.stamp));
      });
      subs_.push_back(sub);
      RCLCPP_INFO(this->get_logger(), "Subscribed to %s", t.c_str());
    }

    status_pub_ = this->create_publisher<std_msgs::msg::String>("/alpha/mapping/status", 10);
    std_msgs::msg::String st;
    st.data = std::string("STARTED ") + provider;
    status_pub_->publish(st);
    RCLCPP_INFO(this->get_logger(), "Mapping node started with provider: %s", provider.c_str());
  }

private:
  std::unique_ptr<IMappingProvider> provider_;
  std::vector<rclcpp::Subscription<PointCloud2>::SharedPtr> subs_;
  std::shared_ptr<pluginlib::ClassLoader<IMappingProvider>> loader_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_pub_;
};

} // namespace alpha_mapping

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<alpha_mapping::MappingNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
