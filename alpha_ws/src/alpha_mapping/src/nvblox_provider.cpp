// Placeholder NVBlox provider implementing IMappingProvider.
#include <memory>
#include <string>
#include <pluginlib/class_list_macros.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>

#include "alpha_mapping/provider_interface.hpp"

namespace alpha_mapping {

class NvbloxProvider : public IMappingProvider {
public:
  NvbloxProvider() = default;
  ~NvbloxProvider() override = default;

  bool configure(rclcpp::Node* node) override {
    node_ = node->shared_from_this();
    RCLCPP_INFO(node_->get_logger(), "NvbloxProvider configured (placeholder)");
    return true;
  }

  void integrateCloud(const std::shared_ptr<sensor_msgs::msg::PointCloud2>& cloud,
                      const std::string& frame_id,
                      const rclcpp::Time& stamp) override {
    (void)frame_id;
    (void)stamp;
    // Placeholder: future integration with isaac_ros_nvblox
    if (last_log_.nanoseconds() == 0 || (node_->now() - last_log_).seconds() > 1.0) {
      RCLCPP_INFO(node_->get_logger(), "NvbloxProvider got cloud %ux%u", cloud->height, cloud->width);
      last_log_ = node_->now();
    }
  }

  void reset() override {
    // Reset internal state (placeholder)
  }

private:
  rclcpp::Node::SharedPtr node_;
  rclcpp::Time last_log_{};
};

} // namespace alpha_mapping

PLUGINLIB_EXPORT_CLASS(alpha_mapping::NvbloxProvider, alpha_mapping::IMappingProvider)

