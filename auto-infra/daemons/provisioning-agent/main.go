package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/gorilla/mux"
)

const (
	// Base paths for customer environments
	BaseCustomerPath = "/var/lib/customers"
	BaseWebRoot      = "/var/www/customers"
	NginxConfigPath  = "/etc/nginx/sites-available"
)

type ProvisionRequest struct {
	CustomerID   string            `json:"customer_id"`
	Email        string            `json:"email"`
	Domain       string            `json:"domain"`
	ServiceType  string            `json:"service_type"` // "web", "database", "storage"
	Plan         string            `json:"plan"`         // "starter", "pro", "business"
	Resources    ResourceAllocation `json:"resources"`
	Metadata     map[string]string `json:"metadata"`
}

type ResourceAllocation struct {
	CPULimit    string `json:"cpu_limit"`     // e.g., "0.5", "1.0"
	MemoryLimit string `json:"memory_limit"`  // e.g., "512M", "2G"
	DiskQuota   string `json:"disk_quota"`    // e.g., "10G", "50G"
}

type ProvisionResponse struct {
	Success    bool              `json:"success"`
	CustomerID string            `json:"customer_id"`
	Message    string            `json:"message"`
	Resources  map[string]string `json:"resources"`
	Error      string            `json:"error,omitempty"`
}

func main() {
	log.Println("Starting provisioning-agent daemon...")

	// Ensure base directories exist
	ensureBaseDirectories()

	// Setup HTTP server
	r := mux.NewRouter()
	r.HandleFunc("/provision", provisionHandler).Methods("POST")
	r.HandleFunc("/deprovision", deprovisionHandler).Methods("POST")
	r.HandleFunc("/health", healthHandler).Methods("GET")
	r.HandleFunc("/status/{customer_id}", statusHandler).Methods("GET")

	port := getEnv("PORT", "8081")
	log.Printf("Listening on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, r))
}

func provisionHandler(w http.ResponseWriter, r *http.Request) {
	var req ProvisionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	log.Printf("Provisioning customer: %s (%s) - %s", req.CustomerID, req.Email, req.ServiceType)

	// Provision based on service type
	var response ProvisionResponse
	var err error

	switch req.ServiceType {
	case "web":
		response, err = provisionWebHosting(req)
	case "database":
		response, err = provisionDatabase(req)
	case "storage":
		response, err = provisionStorage(req)
	default:
		respondError(w, "Unknown service type", http.StatusBadRequest)
		return
	}

	if err != nil {
		log.Printf("Provisioning failed: %v", err)
		response = ProvisionResponse{
			Success:    false,
			CustomerID: req.CustomerID,
			Error:      err.Error(),
		}
		w.WriteHeader(http.StatusInternalServerError)
	} else {
		log.Printf("✅ Provisioned successfully: %s", req.CustomerID)
		response.Success = true
		w.WriteHeader(http.StatusOK)
	}

	json.NewEncoder(w).Encode(response)
}

func provisionWebHosting(req ProvisionRequest) (ProvisionResponse, error) {
	customerPath := filepath.Join(BaseCustomerPath, req.CustomerID)
	webRoot := filepath.Join(BaseWebRoot, req.CustomerID)

	// Create directory structure
	dirs := []string{
		customerPath,
		webRoot,
		filepath.Join(webRoot, "public_html"),
		filepath.Join(webRoot, "logs"),
		filepath.Join(customerPath, "ssl"),
	}

	for _, dir := range dirs {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return ProvisionResponse{}, fmt.Errorf("failed to create directory %s: %w", dir, err)
		}
	}

	// Create nginx configuration
	nginxConfig := fmt.Sprintf(`server {
    listen 80;
    server_name %s;

    root %s/public_html;
    index index.html index.php;

    access_log %s/logs/access.log;
    error_log %s/logs/error.log;

    # PHP-FPM configuration
    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php8.2-fpm-%s.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }

    # Resource limits
    client_max_body_size 100M;

    # Static file caching
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
`, req.Domain, webRoot, webRoot, webRoot, req.CustomerID)

	configFile := filepath.Join(NginxConfigPath, req.Domain+".conf")
	if err := os.WriteFile(configFile, []byte(nginxConfig), 0644); err != nil {
		return ProvisionResponse{}, fmt.Errorf("failed to write nginx config: %w", err)
	}

	// Enable site
	enabledPath := strings.Replace(NginxConfigPath, "sites-available", "sites-enabled", 1)
	symlinkPath := filepath.Join(enabledPath, req.Domain+".conf")
	os.Symlink(configFile, symlinkPath)

	// Create PHP-FPM pool
	phpPoolConfig := fmt.Sprintf(`[%s]
user = www-data
group = www-data
listen = /var/run/php/php8.2-fpm-%s.sock
listen.owner = www-data
listen.group = www-data
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3

; Resource limits
php_admin_value[memory_limit] = %s
php_admin_value[upload_max_filesize] = 50M
php_admin_value[post_max_size] = 50M
`, req.CustomerID, req.CustomerID, req.Resources.MemoryLimit)

	phpPoolFile := fmt.Sprintf("/etc/php/8.2/fpm/pool.d/%s.conf", req.CustomerID)
	if err := os.WriteFile(phpPoolFile, []byte(phpPoolConfig), 0644); err != nil {
		return ProvisionResponse{}, fmt.Errorf("failed to write PHP-FPM config: %w", err)
	}

	// Create default index page
	indexHTML := fmt.Sprintf(`<!DOCTYPE html>
<html>
<head>
    <title>Welcome to %s</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        .info { background: #f0f0f0; padding: 20px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Welcome to your new hosting account!</h1>
    <div class="info">
        <p><strong>Customer ID:</strong> %s</p>
        <p><strong>Plan:</strong> %s</p>
        <p>Your hosting environment is ready. Upload your files to get started!</p>
    </div>
</body>
</html>
`, req.Domain, req.CustomerID, req.Plan)

	indexPath := filepath.Join(webRoot, "public_html", "index.html")
	os.WriteFile(indexPath, []byte(indexHTML), 0644)

	// Reload services
	exec.Command("systemctl", "reload", "nginx").Run()
	exec.Command("systemctl", "reload", "php8.2-fpm").Run()

	return ProvisionResponse{
		CustomerID: req.CustomerID,
		Message:    "Web hosting provisioned successfully",
		Resources: map[string]string{
			"webroot":     webRoot + "/public_html",
			"domain":      req.Domain,
			"ftp_user":    req.CustomerID,
			"php_version": "8.2",
		},
	}, nil
}

func provisionDatabase(req ProvisionRequest) (ProvisionResponse, error) {
	// TODO: Implement database provisioning
	// - Create PostgreSQL database and user
	// - Set connection limits based on plan
	// - Configure pgbouncer pool
	return ProvisionResponse{
		CustomerID: req.CustomerID,
		Message:    "Database provisioning not yet implemented",
	}, nil
}

func provisionStorage(req ProvisionRequest) (ProvisionResponse, error) {
	// TODO: Implement S3-compatible storage provisioning
	// - Create MinIO bucket
	// - Generate access keys
	// - Set quota limits
	return ProvisionResponse{
		CustomerID: req.CustomerID,
		Message:    "Storage provisioning not yet implemented",
	}, nil
}

func deprovisionHandler(w http.ResponseWriter, r *http.Request) {
	var req struct {
		CustomerID string `json:"customer_id"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	log.Printf("Deprovisioning customer: %s", req.CustomerID)

	// Remove customer directories
	customerPath := filepath.Join(BaseCustomerPath, req.CustomerID)
	webRoot := filepath.Join(BaseWebRoot, req.CustomerID)
	os.RemoveAll(customerPath)
	os.RemoveAll(webRoot)

	// Remove nginx config
	nginxConfigGlob := filepath.Join(NginxConfigPath, "*.conf")
	configs, _ := filepath.Glob(nginxConfigGlob)
	for _, config := range configs {
		if strings.Contains(config, req.CustomerID) {
			os.Remove(config)
		}
	}

	// Remove PHP-FPM pool
	phpPoolFile := fmt.Sprintf("/etc/php/8.2/fpm/pool.d/%s.conf", req.CustomerID)
	os.Remove(phpPoolFile)

	// Reload services
	exec.Command("systemctl", "reload", "nginx").Run()
	exec.Command("systemctl", "reload", "php8.2-fpm").Run()

	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":     true,
		"customer_id": req.CustomerID,
		"message":     "Customer deprovisioned successfully",
	})
}

func statusHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	customerID := vars["customer_id"]

	customerPath := filepath.Join(BaseCustomerPath, customerID)
	webRoot := filepath.Join(BaseWebRoot, customerID)

	status := map[string]interface{}{
		"customer_id": customerID,
		"exists":      dirExists(customerPath),
		"webroot":     dirExists(webRoot),
	}

	json.NewEncoder(w).Encode(status)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	json.NewEncoder(w).Encode(map[string]string{
		"status": "healthy",
		"daemon": "provisioning-agent",
	})
}

func ensureBaseDirectories() {
	os.MkdirAll(BaseCustomerPath, 0755)
	os.MkdirAll(BaseWebRoot, 0755)
}

func dirExists(path string) bool {
	info, err := os.Stat(path)
	if os.IsNotExist(err) {
		return false
	}
	return info.IsDir()
}

func respondError(w http.ResponseWriter, message string, code int) {
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(map[string]string{
		"error": message,
	})
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
