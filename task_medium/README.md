### **Extended Asymmetric Laplace (exAL) Distribution in C++ for R**

#### **Overview**
This project implements the **Extended Asymmetric Laplace (exAL) distribution** in **C++** using **Rcpp** for efficient numerical computations. The implementation is based on **Yan and Kottas (2017)** and follows a **robust, high-performance design** to ensure numerical stability and efficiency.

The package provides **four core functions** for working with the exAL distribution:  
- **`dexal(x, p0, mu, sigma, gamma, log = FALSE)`**: Computes the probability density function (PDF).
- **`pexal(q, p0, mu, sigma, gamma, lower.tail = TRUE, log.p = FALSE)`**: Computes the cumulative distribution function (CDF).
- **`qexal(p, p0, mu, sigma, gamma, lower.tail = TRUE, log.p = FALSE)`**: Computes the quantile function (inverse CDF).
- **`rexal(n, p0, mu, sigma, gamma)`**: Generates random samples.

All functions are exposed to **R** using `Rcpp`, ensuring high performance while integrating with R workflows.

---

## **Installation**
Before using the package, ensure you have the required dependencies installed:

```r
install.packages("Rcpp")
install.packages("RcppArmadillo")
install.packages("ggplot2")  # For visualization
```

Then, compile the C++ source file within R:

```r
library(Rcpp)
Rcpp::sourceCpp("src/exAL.cpp")  # Adjust path as needed
```

---

## **The exAL Distribution**
The **Extended Asymmetric Laplace (exAL)** distribution extends the standard **Asymmetric Laplace (AL) distribution** by incorporating an additional skewness parameter **γ (gamma)**. This parameter controls the asymmetry of the distribution while maintaining analytical tractability.

### **Probability Density Function (PDF)**
For a given **quantile level** `p0 ∈ (0,1)`, the exAL density function is defined as:

$$
f(y \mid p_0, \mu, \sigma, \gamma) = \int_{\mathbb{R}^+} f_{AL}(y \mid p_0, \mu + \sigma |\alpha| s, \sigma)  N^+(s \mid 0, 1) ds
$$

where $ f_{AL} $ is the Asymmetric Laplace density, and $ N^+(s \mid 0,1) $ represents the **half-normal** distribution.

The exAL distribution admits several **infinite mixture representations**, including:
1. **AL as a Normal-Exponential Mixture**
2. **GAL as AL-Half-Normal Mixture**
3. **GAL as Double Mixture (Normal-Exp-Half-Normal)**

### **Alternative Parameterization**
The exAL distribution can be reparameterized using `p0` and `γ` instead of the usual `p` and `α`:

$$
p = \mathbf{1}(\gamma<0) + \frac{p_0 - \mathbf{1}(\gamma<0)}{g(\gamma)}
$$

$$
\alpha = \frac{|\gamma|}{\mathbf{1}(\gamma>0) - p}
$$

where:

$$
g(\gamma) = 2\Phi(-|\gamma|)e^{\gamma^2/2}
$$

The **γ parameter is restricted** to an interval **(L, U)**, which ensures well-defined distribution properties.

---

## **Implemented Functions**
### **1. Probability Density Function (PDF)**
```r
dexal(x, p0, mu, sigma, gamma, log = FALSE)
```
- Computes the exAL density function.
- Supports log-scale computations for numerical stability.

### **2. Cumulative Distribution Function (CDF)**
```r
pexal(q, p0, mu, sigma, gamma, lower.tail = TRUE, log.p = FALSE)
```
- Computes the cumulative probability up to `q`.
- Supports **log-scale probabilities** and **upper-tail probabilities**.

### **3. Quantile Function (Inverse CDF)**
```r
qexal(p, p0, mu, sigma, gamma, lower.tail = TRUE, log.p = FALSE)
```
- Computes the inverse CDF, providing the **quantile function**.
- Uses an efficient root-finding algorithm.

### **4. Random Sampling**
```r
rexal(n, p0, mu, sigma, gamma)
```
- Generates `n` independent random draws from the exAL distribution.
- Uses a combination of the AL and Half-Normal distributions.

---

## **Performance Optimization**
- **Implemented in C++** for efficiency.
- Uses **Boost root-finding** for accurate quantile estimation.
- Carefully handles **numerical underflow** issues.

---

## **References**
- Yan, Y., & Kottas, A. (2017). A new family of error distributions for Bayesian quantile regression. arXiv preprint arXiv:1701.05666. https://arxiv.org/abs/1701.05666

---

## **Contributing**
Contributions are welcome! If you find issues or want to add features:
1. Fork the repository.
2. Make changes and test them.
3. Submit a pull request.

---

## **License**
This project is released under the **MIT License**.

