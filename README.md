# WAU

WoW Addons Updater
WoW插件更新器

参考了<https://github.com/oyishi/TTui>，用Python重新实现了。

主要功能就是查找curse和wowace，跟本地文件比较（实际上是本地cache，不是插件文件本身），如果有更新，就重新下载，解压。

使用方法：
1.可能需要少量的python知识。

2.生成一份配置文件`config.yaml`，工程里有一个例子`config.yaml.example`，把他改名成`config.yaml`即可。当然这里面信息肯定不对，需要自己修改。其实yaml文件的结构还是挺简单的，请自己领悟，当然也可以去搜一下yaml文件的相关知识。

3.安装python，然后缺什么包就装什么包（其实是我也忘了应该装那些包了，有人全新安装的话，可以帮着补充一下这部分知识），然后`python WAU.py`，或者直接双击`WAU.bat`。

4.理论上讲可以支持mac，不过也需要一些python知识，和终端窗口操作技能。
