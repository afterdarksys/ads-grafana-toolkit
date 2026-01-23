package main

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/shirou/gopsutil/v3/net"
)

const (
	// Capacity thresholds
	CPUThreshold    = 80.0
	MemoryThreshold = 80.0
	DiskThreshold   = 80.0

	// Monitoring interval
	CheckInterval = 30 * time.Second

	// Alert cooldown (prevent alert spam)
	AlertCooldown = 5 * time.Minute

	// Prometheus metrics port
	MetricsPort = ":9100"
)

type CapacityMetrics struct {
	Timestamp      time.Time `json:"timestamp"`
	Hostname       string    `json:"hostname"`
	InstanceID     string    `json:"instance_id"`
	CPUPercent     float64   `json:"cpu_percent"`
	MemoryPercent  float64   `json:"memory_percent"`
	DiskPercent    float64   `json:"disk_percent"`
	NetworkRxBytes uint64    `json:"network_rx_bytes"`
	NetworkTxBytes uint64    `json:"network_tx_bytes"`
	IsOverCapacity bool      `json:"is_over_capacity"`
}

type Config struct {
	N8nWebhookURL  string
	MetricsAPIURL  string
	InstanceID     string
	Hostname       string
	AlertThreshold float64
}

var (
	config        Config
	lastAlertTime time.Time

	// Prometheus metrics
	cpuUsage = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "capacity_monitor_cpu_percent",
			Help: "Current CPU usage percentage",
		},
		[]string{"hostname", "instance_id"},
	)
	memoryUsage = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "capacity_monitor_memory_percent",
			Help: "Current memory usage percentage",
		},
		[]string{"hostname", "instance_id"},
	)
	diskUsage = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "capacity_monitor_disk_percent",
			Help: "Current disk usage percentage",
		},
		[]string{"hostname", "instance_id"},
	)
	networkRxBytes = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "capacity_monitor_network_rx_bytes_total",
			Help: "Total network bytes received",
		},
		[]string{"hostname", "instance_id"},
	)
	networkTxBytes = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "capacity_monitor_network_tx_bytes_total",
			Help: "Total network bytes transmitted",
		},
		[]string{"hostname", "instance_id"},
	)
	capacityStatus = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "capacity_monitor_over_capacity",
			Help: "Whether instance is over capacity (1) or not (0)",
		},
		[]string{"hostname", "instance_id"},
	)
)

func init() {
	// Register Prometheus metrics
	prometheus.MustRegister(cpuUsage)
	prometheus.MustRegister(memoryUsage)
	prometheus.MustRegister(diskUsage)
	prometheus.MustRegister(networkRxBytes)
	prometheus.MustRegister(networkTxBytes)
	prometheus.MustRegister(capacityStatus)
}

func main() {
	log.Println("Starting capacity-monitor daemon...")

	// Load configuration
	config = loadConfig()

	// Start Prometheus metrics HTTP server
	go startMetricsServer()

	// Main monitoring loop
	ticker := time.NewTicker(CheckInterval)
	defer ticker.Stop()

	// Run initial check immediately
	runCheck()

	for range ticker.C {
		runCheck()
	}
}

func startMetricsServer() {
	http.Handle("/metrics", promhttp.Handler())
	log.Printf("Starting Prometheus metrics server on %s", MetricsPort)
	if err := http.ListenAndServe(MetricsPort, nil); err != nil {
		log.Fatalf("Failed to start metrics server: %v", err)
	}
}

func loadConfig() Config {
	hostname, _ := os.Hostname()
	instanceID := os.Getenv("OCI_INSTANCE_ID")
	if instanceID == "" {
		// Try to get from metadata service
		instanceID = getInstanceIDFromMetadata()
	}

	return Config{
		N8nWebhookURL:  getEnv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/capacity-alert"),
		MetricsAPIURL:  getEnv("METRICS_API_URL", "http://localhost:8080/api/metrics"),
		InstanceID:     instanceID,
		Hostname:       hostname,
		AlertThreshold: CPUThreshold,
	}
}

func runCheck() {
	metrics := collectMetrics()

	// Log current metrics
	log.Printf("CPU: %.2f%%, Memory: %.2f%%, Disk: %.2f%%",
		metrics.CPUPercent, metrics.MemoryPercent, metrics.DiskPercent)

	// Send metrics to API
	sendMetricsToAPI(metrics)

	// Check if we need to alert
	if metrics.IsOverCapacity && shouldSendAlert() {
		sendAlert(metrics)
		lastAlertTime = time.Now()
	}
}

func collectMetrics() CapacityMetrics {
	metrics := CapacityMetrics{
		Timestamp:  time.Now(),
		Hostname:   config.Hostname,
		InstanceID: config.InstanceID,
	}

	labels := prometheus.Labels{
		"hostname":    config.Hostname,
		"instance_id": config.InstanceID,
	}

	// CPU usage
	cpuPercent, err := cpu.Percent(time.Second, false)
	if err == nil && len(cpuPercent) > 0 {
		metrics.CPUPercent = cpuPercent[0]
		cpuUsage.With(labels).Set(metrics.CPUPercent)
	}

	// Memory usage
	memInfo, err := mem.VirtualMemory()
	if err == nil {
		metrics.MemoryPercent = memInfo.UsedPercent
		memoryUsage.With(labels).Set(metrics.MemoryPercent)
	}

	// Disk usage (root partition)
	diskInfo, err := disk.Usage("/")
	if err == nil {
		metrics.DiskPercent = diskInfo.UsedPercent
		diskUsage.With(labels).Set(metrics.DiskPercent)
	}

	// Network stats
	netStats, err := net.IOCounters(false)
	if err == nil && len(netStats) > 0 {
		metrics.NetworkRxBytes = netStats[0].BytesRecv
		metrics.NetworkTxBytes = netStats[0].BytesSent
		networkRxBytes.With(labels).Set(float64(metrics.NetworkRxBytes))
		networkTxBytes.With(labels).Set(float64(metrics.NetworkTxBytes))
	}

	// Determine if over capacity
	metrics.IsOverCapacity = metrics.CPUPercent >= CPUThreshold ||
		metrics.MemoryPercent >= MemoryThreshold ||
		metrics.DiskPercent >= DiskThreshold

	// Update capacity status metric
	if metrics.IsOverCapacity {
		capacityStatus.With(labels).Set(1)
	} else {
		capacityStatus.With(labels).Set(0)
	}

	return metrics
}

func sendMetricsToAPI(metrics CapacityMetrics) {
	jsonData, err := json.Marshal(metrics)
	if err != nil {
		log.Printf("Error marshaling metrics: %v", err)
		return
	}

	resp, err := http.Post(config.MetricsAPIURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		log.Printf("Error sending metrics to API: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Metrics API returned non-OK status: %d", resp.StatusCode)
	}
}

func sendAlert(metrics CapacityMetrics) {
	alertData := map[string]interface{}{
		"alert_type": "capacity_threshold_exceeded",
		"timestamp":  metrics.Timestamp,
		"instance": map[string]string{
			"id":       metrics.InstanceID,
			"hostname": metrics.Hostname,
		},
		"metrics": map[string]float64{
			"cpu_percent":    metrics.CPUPercent,
			"memory_percent": metrics.MemoryPercent,
			"disk_percent":   metrics.DiskPercent,
		},
		"recommended_action": "scale_up",
		"scale_amount":       "15-20%",
	}

	jsonData, err := json.Marshal(alertData)
	if err != nil {
		log.Printf("Error marshaling alert: %v", err)
		return
	}

	log.Printf("🚨 CAPACITY ALERT: Sending to n8n webhook...")
	resp, err := http.Post(config.N8nWebhookURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		log.Printf("Error sending alert to n8n: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		log.Printf("✅ Alert sent successfully to n8n")
	} else {
		log.Printf("❌ n8n webhook returned status: %d", resp.StatusCode)
	}
}

func shouldSendAlert() bool {
	if lastAlertTime.IsZero() {
		return true
	}
	return time.Since(lastAlertTime) >= AlertCooldown
}

func getInstanceIDFromMetadata() string {
	// OCI metadata service
	resp, err := http.Get("http://169.254.169.254/opc/v1/instance/id")
	if err != nil {
		return "unknown"
	}
	defer resp.Body.Close()

	buf := new(bytes.Buffer)
	buf.ReadFrom(resp.Body)
	return buf.String()
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
